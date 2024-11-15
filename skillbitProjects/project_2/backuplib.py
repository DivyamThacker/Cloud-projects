import boto3
import os
from cryptography.fernet import Fernet
import schedule
import time
from datetime import datetime
import sys, argparse

s3 = boto3.client('s3')

#defining the argument parser
argparser = argparse.ArgumentParser(description="This is the Main program that backups your files :)")
argsubparsers = argparser.add_subparsers(title="Commands", dest="command")
argsubparsers.required = True

def main(argv=sys.argv[1:]):
    args = argparser.parse_args(argv)
    if args.command == "backup":
        cmd_backup(args)
    elif args.command == "encrypt":
        cmd_encrypt(args)
    elif args.command == "decrypt":
        cmd_decrypt(args)
    elif args.command == "help":
        welcome()
    else:
        print("Bad Command")

argsp = argsubparsers.add_parser("help", help="Get to know about all the commands")  

def say_hello():
    print("Hello, World!")

def welcome():
    print("Welcome to SBS - A Scheduled Backup System.")
    print("Created by - Divyam Thacker\n")
    print("This program will help you backup your files to an S3 bucket.")
    print("python main.py backup : the oneline backup command")
    print("python main.py encrypt : encrypt the file")
    print("python main.py decrypt : decrypt the file with the provided key\n\n")

argsp = argsubparsers.add_parser("backup", help="Initiate the backup process with the given parameters")
argsp.add_argument("path", help="The local directory path or file path you want to backup")
argsp.add_argument("bucket", help="The S3 bucket name where you want to backup")
argsp.add_argument("--prefix", default="backup/", help="The S3 prefix for the backup")
argsp.add_argument("-e", dest="encryption_flag" ,default=False, action="store_true", help="Enable encryption for the backup")
argsp.add_argument("--versioning", default=False, action="store_true", help="Enable versioning for the S3 bucket")
argsp.add_argument("--encryption-key",dest="key", default=Fernet.generate_key(), help="The encryption key (if encryption is enabled)")
argsp.add_argument("--schedule", default= "once", choices=["once","minutely", "hourly", "daily", "monthly", "half-yearly", "yearly"],
                    help="Enable scheduling for the backup")

# Main function for command-line arguments
def cmd_backup(args):
    if args.encryption_flag:
        print(f"Encryption key: {args.key.decode()} , save it for decryption later")
    configure_versioning(args.bucket, args.versioning)
    schedule_tasks(
        args.schedule,
        lambda: perform_backup(args.path, args.bucket, args.prefix, args.encryption_flag, args.key)
    )

argsp = argsubparsers.add_parser("encrypt", help="Encrypt a given file with the provided or generated key")
argsp.add_argument("path", help="The local directory path or file path you want to backup")
argsp.add_argument("--encryption-key", dest="key",default= Fernet.generate_key , help="The encryption key (if encryption is enabled)")


def cmd_encrypt(args):
    print(f"The encryption key is {args.key}, save for later decryption")
    if os.path.isdir(args.path):
        for root, _, files in os.walk(args.path):
            for file in files:
                file_path = os.path.join(root, file)
                encrypt_file(file_path, args.key)
    elif os.path.isfile(args.path):
        encrypt_file(args.path, args.key)
    else:
        print(f"Error: {args.path} is not a valid file or directory")

argsp = argsubparsers.add_parser("decrypt", help="Decrypt a given file with the provided or generated key")
argsp.add_argument("path", help="The local directory path or file path you want to backup")
argsp.add_argument("key", help="The encryption key (if encryption is enabled)")

def cmd_decrypt(args):
    if os.path.isdir(args.path):
        for root, _, files in os.walk(args.path):
            for file in files:
                file_path = os.path.join(root, file)
                decrypt_file(file_path, args.key)
    elif os.path.isfile(args.path):
        decrypt_file(args.path, args.key)
    else:
        print(f"Error: {args.path} is not a valid file or directory")

# Encryption function
def encrypt_file(file_path, key):
    with open(file_path, 'rb') as f:
        data = f.read()
    encrypted_data = Fernet(key).encrypt(data)
    with open(file_path, 'wb') as f:
        f.write(encrypted_data)

# Decryption function (optional, for restoring files)
def decrypt_file(file_path, key):
    with open(file_path, 'rb') as f:
        encrypted_data = f.read()
    decrypted_data = Fernet(key).decrypt(encrypted_data)
    with open(file_path, 'wb') as f:
        f.write(decrypted_data)

# Common function to backup a file
def backup_file(file_path, bucket, prefix, encryption_flag=False, key=None):
    print(f"Backing up {file_path}...")
    if encryption_flag:
        encrypt_file(file_path, key)

    s3_path = os.path.join(prefix, os.path.relpath(file_path, os.getcwd()))
    print(f"Uploading to S3: {bucket}/{s3_path}")
    s3.upload_file(file_path, bucket, s3_path)
    print(f"Successfully backed up {file_path} to S3: {s3_path}")

    if encryption_flag:
        decrypt_file(file_path, key)

# Common function to perform a backup
def perform_backup(path, bucket, prefix, encryption_flag=False, key=None):
    print(f"Starting backup at {datetime.now()}...")
    if os.path.isdir(path):
        for root, _, files in os.walk(path):
            for file in files:
                local_path = os.path.join(root, file)
                backup_file(local_path, bucket, prefix, encryption_flag, key)
    elif os.path.isfile(path):
        backup_file(path, bucket, prefix, encryption_flag, key)
    else:
        print(f"Error: {path} is not a valid file or directory")

# Common function to enable or suspend versioning
def configure_versioning(bucket, enable):
    versioning_status = "Enabled" if enable else "Suspended"
    s3.put_bucket_versioning(
        Bucket=bucket,
        VersioningConfiguration={'Status': versioning_status}
    )

# Common function to schedule tasks
def schedule_tasks(schedule_option, backup_function):
    schedule_option = schedule_option.lower()
    if schedule_option == "once":
        backup_function()
    elif schedule_option == "minutely":
        schedule.every().minute.do(backup_function)
    elif schedule_option == "hourly":
        schedule.every().hour.do(backup_function)
    elif schedule_option == "daily":
        schedule.every().day.at("00:00").do(backup_function)
    elif schedule_option == "monthly":
        schedule.every(30).days.at("00:00").do(backup_function)
    elif schedule_option == "half-yearly":
        schedule.every(182).days.at("00:00").do(backup_function)
    elif schedule_option == "yearly":
        schedule.every(365).days.at("00:00").do(backup_function)
    else:
        print("Invalid schedule option. Performing backup once.")
        backup_function()

    while schedule_option != "once":
        schedule.run_pending()
        time.sleep(1)

# Function to handle user input and perform backup
def interactive_backup():
    path = input("Enter the complete local directory or file path to backup: ")
    bucket = input("Enter the S3 bucket name: ")
    prefix = input("Enter the S3 prefix for the backup: ")

    encryption_flag = input("Enable encryption? (y/n): ").strip().lower() == "y"
    key = None
    if encryption_flag:
        use_custom_key = input("Provide your own encryption key? (y/n): ").strip().lower() == "y"
        if use_custom_key:
            key = input("Enter your encryption key: ").encode()
        else:
            key = Fernet.generate_key()
            print(f"Generated encryption key: {key.decode()} , save it for decryption later")

    versioning = input("Enable versioning for the S3 bucket? (y/n): ").strip().lower() == "y"
    configure_versioning(bucket, versioning)

    is_scheduling_enabled = input("Enable scheduling for the backup? (y/n): ").strip().lower() == "y"
    if is_scheduling_enabled:
        print("Choose a schedule option:")
        print("1. Once\n2. Minutely\n3. Hourly\n4. Daily\n5. Monthly\n6. Half-yearly\n7. Yearly")
        schedule_option = input("Enter your choice: ").strip()

        schedule_tasks(schedule_option, lambda: perform_backup(path, bucket, prefix, encryption_flag, key))
    else:
        perform_backup(path, bucket, prefix, encryption_flag, key)


