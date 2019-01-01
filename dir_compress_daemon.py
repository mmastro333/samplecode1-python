#!/usr/bin/python
#NAME: Michael Mastrogiacomo
#DATE: 09-27-2018
#PURPOSE:  
# A daemon that regularly scans a directory for files to compress and emails a report on its activity.  
#INSTALL NOTES:  
#   You'll need Python 3.x or higher.
#   You'll need to ensure these additional modules are installed:  
#   pip install validate-email-address
#   pip install psutil
#REFERENCE: 
# https://stackoverflow.com/questions/1112343/how-do-i-capture-sigint-in-python
# https://docs.python.org/2/library/getopt.html
# https://stackoverflow.com/questions/2532053/validate-a-hostname-string


import re,platform,getopt,sys,os,gzip,shutil,signal,psutil,time,datetime,smtplib
from validate_email_address import validate_email


# Define a class for handling the SIGTERM signal; when a SIGTERM is caught handler.SIGTERM will return "True"
class SIGTERM_handler():
    def __init__(self):
        self.SIGTERM = False

    def signal_handler(self, signal, frame):
        print('SIGTERM signal received...preparing to stop process...(note you might have to wait the length of the specified sleep period)...')
        self.SIGTERM = True



# Function to validate a hostname
def is_valid_hostname(hostname):
    if len(hostname) > 255:
        return False
    if hostname[-1] == ".":
        hostname = hostname[:-1] # strip exactly one dot from the right, if present
    allowed = re.compile("(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
    return all(allowed.match(x) for x in hostname.split("."))



# Function to check if a given file has a file handle associated with it (i.e. check if the file is in use)
# reference: https://stackoverflow.com/questions/11114492/check-if-a-file-is-not-open-not-used-by-other-process-in-python/11115521
def has_handle(fpath):
    for proc in psutil.process_iter():
        try:
            for item in proc.open_files():
               if os.path.abspath(fpath) == item.path:
                  return True
        except:
           pass
           
    return False


# Function to extract file extension from a filename (i.e. ".gz" from "f.gz")
def get_file_ext(f):
   extension = os.path.splitext(f)[1]
   return extension


# Function to display usage
# Requirement: 1. The program displays a help/usage summary when called with the -h option
def usage():
   print("Usage:  ")
   print(sys.argv[0] +  " [-r] [-h] [-s <seconds_to_sleep>] [-m <user@domain>] [-e <smtp_host>] <target_dir> <email_address> <file_size_threshold>")
   print("   where: ")
   print(" <target_dir>: Specifies the directory to crawl")
   print(" <email_address>: Specifies the email address to receive the file compressions report")
   print(" <file_size_threshold>: Specifies the cut off threshold in bytes for the minimum file size to attempt to compress")
   print(" -r (optional): Specifies that this is a dry run; only report what would be done but do actually create any compressed files")
   print(" -h (optional): Prints help/usage information and exits")
   print(" -s <seconds_to_sleep> (optional): Sleep this specified number of seconds between directory scans")
   print(" -m <sender_email_address> (optional): the email address of the account you are emailing the report from")
   print(" -e <smtp_host> (optional): the smtp host to connect to")


# Function for creating a time stamped string for prepending to all console output messages
# Requirement: 7. The program should produce a reasonable output about what's it's doing, with proper timestamps at the beginning of each line
# This returns a string that looks like "INFO: 18-09-27-12-53-59:" for prepending to console messages
def msg_prepend(err_level):
   stamp = str(datetime.datetime.now().strftime("%y-%m-%d-%H-%M-%S"))
   return(err_level + ": " + str(stamp) + ": ")


# Function for emailing a report of the last directory scan
def send_email_report(smtp_host,target_dir,sender,email_address,compressed_files_list, skipped_small_files_list, disk_space_savings, absolute_filename):

   receivers = [ email_address ]

   message = "From: " + "Directory Compression Daemon"  + " <" + sender + ">\n"
   message += "To: Unknown <" + email_address + ">\n"
   message += "Subject: Directory Compression Report for " + target_dir + "\n"
   message += "\n---Begin report---\n" 
   message += "Disk space total savings: " + str(disk_space_savings) + " bytes\n"
   message += "Compressed files list:\n"
   message += str(compressed_files_list)
   message += "\nSkipped files list:\n" 
   message += str(skipped_small_files_list)
   message += "\n---End report---\n"

   try:
      smtpObj = smtplib.SMTP(smtp_host)
      smtpObj.sendmail(sender, receivers, message)         
      print(msg_prepend("INFO") + "Successfully sent email")
   except SMTPException as smtperr:
      print(msg_prepend("ERROR") + "Unable to send email: " + str(smtperr))



############################
# Begin Main
############################


handler = SIGTERM_handler() #spawn a SIGTERM handler object for handling kill -SIGTERM signals
signal.signal(signal.SIGTERM, handler.signal_handler) # register the SIGTERM handler to handle when a kill -SIGTERM signal is received




# check for minimal python version
if sys.version_info[0] < 3:
   print("You must run this script with Python 3.x or higher")
   sys.exit(1)




##############################################
# Process command line args/options given
##############################################
   


try:
   opts, args = getopt.getopt(sys.argv[1:], "hrs:m:e:")
except getopt.GetoptError as err:
         # print help information and exit:
         print(msg_prepend("ERROR") + str(err))  # will print something like "option -a not recognized"
         usage()
         sys.exit(1)



# Validate minimum number of required args were given 
if len(args) < 3:
   print(msg_prepend("ERROR") + "The minimum required number of command line arguments was not given.")
   usage()
   sys.exit(1)



#################################
# Handle some initialization
##################################

dryrun = False  # initialize
sleep_time = 300  # initialize to default 5 minutes


# initialize and setup a default sender or "mail from" adddress
hostname = platform.node()
user_id = os.getlogin()
sender = str(user_id) + "@" + str(hostname) # i.e. sender address will be something like 'ec2-user@localhost'
# initialize smtp_host
smtp_host = 'localhost' # initialize




compressed_files_list = [] #initialize the list of files that were compressed by this script

skipped_small_files_list = [] # initialize the list of files that were determined to be less than the size of the user provided threshold

a_file_found = False # initialize for handling edge case of an empty root directory

disk_space_savings = 0 # initialize




# Process the command line options given
for o, a in opts: 
        if o == "-h":
           usage()
           sys.exit(0) #exit peacefully since user just wants to see the usage
        elif o == "-r":
           # set flag to perform dry run 
           dryrun = True
        elif o == "-m":
           # set the sender_email_address to what was specified on the command line
           sender = a
        elif o == "-e":
           # set smtp_host to what was specified on the command line
           smtp_host = a
        elif o == "-s":
           # user specified number of seconds to sleep between iterations
           try:
              sleep_time = int(a)
           except:
              print(msg_prepend("ERROR") + "Bad argument given for the number of seconds for the sleep option")
              usage()
              sys.exit(1)
      




##################
# Define args
##################

#requirement: 2. The program accepts one directory as an argument 
target_dir = args[0]

#requirement: 3. The program accepts one email address as an argument 
email_address = args[1]

#requirement: 4. The program accepts one file size threshold as an argument 
file_size_threshold = args[2]




#################
# Validate args
#################

#requirement: 5. The program should reasonably check for invalid arguments and error conditions 


# validate target_dir: Ensure we can access user specified directory
if not(os.access(target_dir, os.R_OK)):
   print(msg_prepend("ERROR") + "Unable to access specified directory: ", target_dir)
   sys.exit(1)



# validate email address
if not(validate_email(email_address)):
   print(msg_prepend("ERROR") + "User specified email address appears to be invalid: ", email_address)
   sys.exit(1)


# validate sender
if not(validate_email(sender)):
   print(msg_prepend("ERROR" + "User specified sender email address appears to be invalid: ", sender))
   sys.exit(1)

# validate smtp_host
if not(is_valid_hostname(smtp_host)):
   print(msg_prepend("ERROR" + "User specified smtp host appears to be invalid: ", smtp_host)) 
   sys.exit(1)



# validate file size threshold
try:
   file_size_threshold = int(args[2])
except:
   print(msg_prepend("ERROR") + "Invalid value specified for file size threshold")
   sys.exit(1)

   





################################
# Entering main loop for daemon
################################


#requirement: 8. The program should run as a daemon and exit cleanly when it receives a SIGTERM kill signal 
while not(handler.SIGTERM):  # main loop for the daemon; it will quit on a SIGTERM signal thanks to the handler_stop_signals function

   for root, dirs, files in os.walk(target_dir, topdown=True):  #traverse the file tree from user specified directory
      for fname in files:

         if platform == "win32":
            absolute_filename = root + '\\' + fname  # handle windows file naming with \
         else:
            absolute_filename = root + '/' + fname   # handle linux file naming with /
     
         compressed_filename = absolute_filename + ".gz"


         print(msg_prepend("INFO") + "Working on file: ", absolute_filename)


         before_compress_size = os.stat(absolute_filename).st_size  #size of the file before compression


         # Skip if compressed:
         # skip already compressed files (i.e. zip/gz/jpg/...) 
         e = get_file_ext(absolute_filename)
         if ( (e == ".tgz") or (e == ".gzip") or (e == ".gz") or (e == ".jpg") or (e == ".jpeg") or (e == ".zip")):
            print(msg_prepend("INFO") + "Skipping already compressed file format ", e)
            skipped_small_files_list.append(absolute_filename)
            continue

         # Skip if too small:
         # Requirement: 1. The program should crawl the specified directory and compress all files larger than the specific size threshold, 
         # except if the compression gain is expected to be small 
         # (already compressed file or jpg format for example) 
         # Check if file size is < file size threshold ... and skip if below threshold to not process small files 
         if before_compress_size < file_size_threshold:
            print(msg_prepend("INFO") + "Skipping file ", absolute_filename, " since file size is below specified threshold of ", file_size_threshold)
            skipped_small_files_list.append(absolute_filename)
            continue


         # Skip if already in use:
         #requirement: 9. The program assumes that any file that is not currently open can safely be compressed  
         # We check here for a open file handle and if present we skip processing the file
         if has_handle(absolute_filename):
            print(msg_prepend("INFO") + "Skipping file ", absolute_filename, " since it is currently in use by another process")
            continue


         a_file_found = True # flag that we found at least one file in the specified directory to compress

      
         # Skip if dry run:
         #requirement: 6. The program provides a dry-run mode
         # If the dryrun option was specfied on the command line, then just print that we'd be creating a compressed file but do nothing really
         if dryrun:
            print(msg_prepend("INFO") + "Creating compressed file: [No files actually are being created due to specified dry-run option]" + compressed_filename)
         else: 
            #############################################
            # Perform the action of compressing the file
            #############################################

            # Copy the file to a compressed version of itself
            print(msg_prepend("INFO") + "Creating compressed file: " + compressed_filename)
            try:
               with open(absolute_filename, 'rb') as f_in, gzip.open(compressed_filename, 'wb') as f_out:
                  shutil.copyfileobj(f_in, f_out)
            except:
               print(msg_prepend("ERROR") + "Error creating compressed file ", compressed_filename)
               sys.exit(2)
         
            # Now delete the original file now that the new compressed version was created
            try:
               print(msg_prepend("INFO") + "Removing original file:" + absolute_filename)
               os.unlink(absolute_filename)
            except:
               print(msg_prepend("ERROR") + "Error deleting file ", absolute_filename)
               sys.exit(3)       




         #########################################
         # Handle additional reporting details
         #########################################
         if not(dryrun):
            after_compress_size = os.stat(compressed_filename).st_size  #size of the file after compression
            disk_space_savings += before_compress_size - after_compress_size  # calculate file size shrinkage and sum it for total savings
         else:
            disk_space_savings = 0  # in dry run this will be somewhat meaningless but accurate
                                    # since we are not actually compressing anything


         # keep a record of the files that were successfully compressed
         compressed_files_list.append(absolute_filename)  
       

         
   #req: 2. The program should send a report to the specified email address with the list of files that were compressed, the total disk space savings and the list of 
   #files that had a too low compression ratio to be considered 
   # Send the email report
   send_email_report(smtp_host,target_dir,sender,email_address,compressed_files_list, skipped_small_files_list, disk_space_savings, absolute_filename)


   # Mention if no files were compressed
   if a_file_found == False:
      print(msg_prepend("INFO") + "No files were found to compress")


   # Truncate the lists now that we've emailed about them to re-initialize for the next iteration (and email report)
   disk_space_savings = 0 # Re-initialize
   compressed_files_list = []  # Re-initialize
   skipped_small_files_list = [] # Re-initialize
   a_file_found = False # Re-initialize
   



   ########################################
   # Sleep between daemon loop iterations
   #########################################
  
   print(msg_prepend("INFO") + "Sleeping " + str(sleep_time) + " seconds between directory scans...")
   time.sleep(sleep_time)


   



