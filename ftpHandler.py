from ftplib import FTP, error_perm, error_temp
from readJSON import Secrets
import sys

def upload_file(ftp, local_path, dest_name):
    """
    Uploads a file as binary code to server
    :param ftp: FTP object logged in to server
    :param local_path: local absolute path to file including filename
    :param dest_name: Desired name of file on server
    :return:
    """
    # The string command used to store the new file
    stor_cmd = "STOR " + dest_name
    with open(local_path, 'rb') as f:
        # perform the upload
        try:
            ftp.storbinary(stor_cmd, f)
            print("File successfully uploaded to server as {}".format(dest_name))
        except error_perm as e:
            print("File transfer failed due to permanent error\n{}".format(e))
        except error_temp as e:
            print("File transfer failed due to temporary error\n{}".format(e))


def download_file(ftp, local_path, file_name):
    """
    Downloads a file as binary code from a server
    :param ftp: FTP object logged into server
    :param local_path: local absolute path including filename
    :param file_name: name of file on server
    :return:
    """
    retr_cmd = "RETR " + file_name
    try:
        ftp.retrbinary(retr_cmd, open(local_path, 'wb').write)
        print("File successfully downloaded to {}".format(local_path))
    except error_perm as e:
        print("File transfer failed due to permanent error\n{}".format(e))
    except error_temp as e:
        print("File transfer failed due to temporary error\n{}".format(e))

def list_files(ftp):
    for file in ftp.nlst():
        print(file)

def list_dir(ftp):
    for file in ftp.dir():
        print(file)


if __name__ == '__main__':
    # Create a Secrets instance to get ftp login requirements
    auth = Secrets()
    # Open FTP connection and login
    ftp = FTP(auth.ftp_host, auth.ftp_user, auth.ftp_pass)
    if sys.argv[1].lower() == 'up':
        upload_file(ftp, sys.argv[2], sys.argv[3])
    elif sys.argv[1].lower() == 'down':
        download_file(ftp, sys.argv[2], sys.argv[3])
    elif sys.argv[1].lower() == 'ls':
        list_files(ftp)
    elif sys.argv[1].lower() == 'dir':
        list_dir(ftp)
    # ftp.quit()


