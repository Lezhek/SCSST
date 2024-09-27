import os
import winreg
import zipfile
import paramiko
import requests
from colorama import init, Fore, Style
from datetime import datetime

init(autoreset=True)

def get_vps_credentials():
    return {
        'hostname': 'your_vps_ip_here',
        'port': 22,
        'vps_username': 'your_vps_usernamehere',
        'vps_password': 'your_vps_ssh_password here'
    }

def get_remote_zip_path(vps_username, steam_username, steamid64):
    return f'/{vps_username}/SnowRunner/{steam_username}\'s save files (Steam ID: {steamid64})/'




def create_remote_directory(sftp, remote_path):
    try:
        sftp.mkdir(remote_path)
        print(Fore.GREEN + f"Created remote directory: {remote_path}")
    except IOError:
        # Directory already exists
        pass
    except Exception as e:
        print(Fore.RED + f"Error creating remote directory: {e}")


def find_steam_folder():
    try:
        # Open the registry key where Steam information is stored
        hkey = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\WOW6432Node\Valve\Steam")

        # Query the registry key for the Steam installation path
        steam_path, _ = winreg.QueryValueEx(hkey, "InstallPath")

        # Close the registry key
        winreg.CloseKey(hkey)

        return steam_path

    except Exception as e:
        print(f"Error accessing Windows Registry: {e}")
        return None

def find_snowrunner_save_folders(steam_folder, files_to_check):
    userdata_folder = os.path.join(steam_folder, 'userdata')
    snowrunner_save_folders = []

    if os.path.exists(userdata_folder) and os.path.isdir(userdata_folder):
        for steam_id_folder in os.listdir(userdata_folder):
            steam_id_path = os.path.join(userdata_folder, steam_id_folder)

            if os.path.isdir(steam_id_path):
                snowrunner_save_path = os.path.join(steam_id_path, '1465360', 'remote')

                if os.path.exists(snowrunner_save_path) and os.path.isdir(snowrunner_save_path):
                    if check_files_exist(snowrunner_save_path, files_to_check):
                        snowrunner_save_folders.append(snowrunner_save_path)

    return snowrunner_save_folders

def check_files_exist(folder_path, file_list):
    for file_name in file_list:
        file_path = os.path.join(folder_path, file_name)
        if not os.path.exists(file_path):
            return False
    return True

def get_valid_choice(max_value):
    while True:
        try:
            choice = int(input(Fore.LIGHTMAGENTA_EX + "Enter the number of the local save folder: "))
            if 1 <= choice <= max_value:
                return choice
            else:
                print(Fore.RED + "Invalid choice. Please enter a number within the range.")
        except ValueError:
            print(Fore.RED+ "Invalid input. Please enter a number.")

def create_zip_archive(source_folder, files_to_zip, zip_path, steam_username):
    timestamp = datetime.now().strftime("%H;%M;%S %d.%m.%Y")
    zip_filename = f"{steam_username}'s Save {timestamp}.zip"

    with zipfile.ZipFile(os.path.join(zip_path, zip_filename), 'w') as zip_file:
        for file_to_zip in files_to_zip:
            file_path = os.path.join(source_folder, file_to_zip)
            if os.path.exists(file_path):
                zip_file.write(file_path, os.path.basename(file_path))

    return zip_filename

def upload_to_vps(local_path, remote_path, hostname, port, username, password):
    transport = paramiko.Transport((hostname, port))
    transport.connect(username=username, password=password)
    sftp = paramiko.SFTPClient.from_transport(transport)

    try:

        # Create the main SnowRunner directory if it doesn't exist
        snowrunner_path = f"/{username}/SnowRunner"
        create_remote_directory(sftp, snowrunner_path)

    
        # Create remote directory if it doesn't exist
        remote_directory = os.path.dirname(remote_path)
        create_remote_directory(sftp, remote_directory)

        print(Fore.GREEN + f"Uploading local file: {local_path}")
        sftp.put(local_path, remote_path)
        return True
    except Exception as e:
        print(Fore.RED + f"Upload failed: {e}")
        return False
    finally:
        sftp.close()
        transport.close()


def list_snowrunner_folders(sftp, vps_username):
    remote_path = f'/{vps_username}/SnowRunner/'
    try:
        folders = sftp.listdir(remote_path)
        print(Fore.GREEN + "Available SnowRunner folders on the remote server:")
        for i, folder in enumerate(folders, start=1):
            print(Fore.LIGHTCYAN_EX + f"{i}. {folder}")
        return folders
    except Exception as e:
        print(Fore.RED + f"Error listing SnowRunner folders: {e}")
        return []

def list_zip_files_in_folder(sftp, folder_path):
    try:
        zip_files = sftp.listdir(folder_path)
        zip_files = [f for f in zip_files if f.endswith('.zip')]  # Filter only zip files
        if not zip_files:
            print(Fore.YELLOW + "No zip files found in the selected folder.")
            return []
        print(Fore.GREEN + "Available zip files:")
        for i, file in enumerate(zip_files, start=1):
            print(Fore.LIGHTCYAN_EX + f"{i}. {file}")
        return zip_files
    except Exception as e:
        print(Fore.RED + f"Error listing zip files: {e}")
        return []

def select_folder_and_zip(sftp, vps_username):
    folders = list_snowrunner_folders(sftp, vps_username)
    if not folders:
        return None, None
    
    try:
        choice = int(input(Fore.LIGHTMAGENTA_EX + "Enter the number of the folder: "))
        if 1 <= choice <= len(folders):
            selected_folder = folders[choice - 1]
            folder_path = f'/{vps_username}/SnowRunner/{selected_folder}/'
            zip_files = list_zip_files_in_folder(sftp, folder_path)
            if zip_files:
                choice = int(input(Fore.LIGHTMAGENTA_EX + "Enter the number of the zip file to download: "))
                if 1 <= choice <= len(zip_files):
                    selected_zip_file = zip_files[choice - 1]
                    return folder_path, selected_zip_file
            return None, None
        else:
            print(Fore.RED + "Invalid choice. Exiting...")
    except ValueError:
        print(Fore.RED + "Invalid input. Please enter a number.")

    return None, None

def list_snowrunner_folders(sftp, vps_username):
    remote_path = f'/{vps_username}/SnowRunner/'
    try:
        folders = sftp.listdir(remote_path)
        print(Fore.GREEN + "Available save folders on the remote server:")
        for i, folder in enumerate(folders, start=1):
            print(Fore.LIGHTCYAN_EX + f"{i}. {folder}")
        return folders
    except Exception as e:
        print(Fore.RED + f"Error listing SnowRunner folders: {e}")
        return []

def list_zip_files_in_folder(sftp, folder_path):
    try:
        zip_files = sftp.listdir(folder_path)
        zip_files = [f for f in zip_files if f.endswith('.zip')]  # Filter only zip files
        if not zip_files:
            print(Fore.YELLOW + "No zip files found in the selected folder.")
            return []
        print(Fore.GREEN + "Available zip files:")
        for i, file in enumerate(zip_files, start=1):
            print(Fore.LIGHTCYAN_EX + f"{i}. {file}")
        return zip_files
    except Exception as e:
        print(Fore.RED + f"Error listing zip files: {e}")
        return []

def select_folder_and_zip(sftp, vps_username):
    folders = list_snowrunner_folders(sftp, vps_username)
    if not folders:
        return None, None
    
    try:
        choice = int(input(Fore.LIGHTMAGENTA_EX + "Enter the number of the folder on remote server: "))
        if 1 <= choice <= len(folders):
            selected_folder = folders[choice - 1]
            folder_path = f'/{vps_username}/SnowRunner/{selected_folder}/'
            zip_files = list_zip_files_in_folder(sftp, folder_path)
            if zip_files:
                choice = int(input(Fore.LIGHTMAGENTA_EX + "Enter the number of the zip file to download: "))
                if 1 <= choice <= len(zip_files):
                    selected_zip_file = zip_files[choice - 1]
                    return folder_path, selected_zip_file
            return None, None
        else:
            print(Fore.RED + "Invalid choice. Exiting...")
    except ValueError:
        print(Fore.RED + "Invalid input. Please enter a number.")

    return None, None


def download_and_unzip_file(hostname, port, vps_username, vps_password, folder_path, selected_zip_file, local_path, save_folder, files_to_delete): 
    transport = paramiko.Transport((hostname, port))
    transport.connect(username=vps_username, password=vps_password)
    sftp = paramiko.SFTPClient.from_transport(transport)

    try:
        # Construct the full remote zip file path
        remote_file_path = f'{folder_path}/{selected_zip_file}'

        # Clear the local save folder for specified files
        cleared_files = []
        for file_to_delete in files_to_delete:
            file_path_to_remove = os.path.join(save_folder, file_to_delete)
            try:
                if os.path.exists(file_path_to_remove):
                    if os.path.isfile(file_path_to_remove):
                        os.unlink(file_path_to_remove)
                    elif os.path.isdir(file_path_to_remove):
                        os.rmdir(file_path_to_remove)
                    cleared_files.append(file_to_delete)
            except Exception as e:
                print(Fore.RED + f"Error clearing local file: {e}")

        if cleared_files:
            print(Fore.BLUE + f"Cleared SnowRunner Save Folder for new save files")

        # Download the selected zip file
        print(Fore.CYAN + f"Downloading save file from: {remote_file_path}")
        sftp.get(remote_file_path, local_path)

        # Unzip the downloaded file
        with zipfile.ZipFile(local_path, 'r') as zip_ref:
            zip_ref.extractall(save_folder)
        
        print(Fore.GREEN + f"Save files downloaded and unzipped successfully to: {save_folder}")

    except Exception as e:
        print(Fore.RED + f"Download and unzip failed: {e}")
        if os.path.exists(local_path):
            os.remove(local_path)
    finally:
        sftp.close()
        transport.close()





def extract_steamid64_from_path(path):
    path_components = os.path.normpath(path).split(os.path.sep)
    userdata_index = path_components.index('userdata')
    steamid3 = path_components[userdata_index + 1]
    steamid64 = str(int(steamid3) + 76561197960265728)
    return steamid64

def get_steam_username(steamid64, api_key):
    url = f'http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={api_key}&steamids={steamid64}'
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        data = response.json()
        player_data = data['response']['players'][0]
        return player_data['personaname']

    except requests.exceptions.RequestException as e:
        print(Fore.RED + f"Error decoding JSON response from Steam API: {e}")
        print(Fore.YELLOW + f"Check your Internet connection")

        return f"UnknownUser(SteamID64)={steamid64}"  # Placeholder username



def main():
    # Get VPS credentials
    vps_creds = get_vps_credentials()  # This should return a dictionary

    # Access the credentials
    vps_hostname = vps_creds['hostname']
    vps_port = vps_creds['port']
    vps_username = vps_creds['vps_username']
    vps_password = vps_creds['vps_password']


    steam_folder = find_steam_folder()

    if steam_folder:
        print(Fore.GREEN + f"Steam folder found: {steam_folder}")

        files_to_check = [
            'user_profile.cfg',
            'user_settings.cfg',
            'user_social_data.cfg',
            'video.cfg'
        ]

        snowrunner_save_folders = find_snowrunner_save_folders(steam_folder, files_to_check)

        if snowrunner_save_folders:
            print(Fore.GREEN + "Local SnowRunner save folders found:")

            # Fetch Steam usernames for each save folder
            api_key = 'insert_your_steam_api_key'
            steam_usernames = []

            for steam_folder_path in snowrunner_save_folders:
                steamid64 = extract_steamid64_from_path(steam_folder_path)
                steam_username = get_steam_username(steamid64, api_key)
                steam_usernames.append(steam_username)

            # Print the associations of folders with usernames
            for i, (folder, username) in enumerate(zip(snowrunner_save_folders, steam_usernames), start=1):
                print(Fore.LIGHTCYAN_EX + f"{i}. {folder} | Steam Username: {Fore.GREEN + username}")

            max_value = len(snowrunner_save_folders)
            choice = get_valid_choice(max_value)
            save_folder = snowrunner_save_folders[choice - 1]
            steamid64 = extract_steamid64_from_path(save_folder)
            steam_username = get_steam_username(steamid64, api_key)

            print(Fore.CYAN + f"Local save folder selected for user: {Fore.GREEN + steam_username}") 

            if check_files_exist(save_folder, files_to_check):
                operation = input(Fore.LIGHTMAGENTA_EX + "Enter 'D' to download save files to the local folder or 'U' to upload SnowRunner save files from the folder to the remote server:").upper()

                if operation == 'D':
                    # Establish SFTP connection
                    transport = paramiko.Transport((vps_hostname, vps_port))
                    transport.connect(username=vps_username, password=vps_password)
                    sftp = paramiko.SFTPClient.from_transport(transport)

                    # Select folder and zip file
                    folder_path, selected_zip_file = select_folder_and_zip(sftp, vps_username)

                    if folder_path and selected_zip_file:
                        remote_file_path = f"{folder_path}{selected_zip_file}"
                        local_path = os.path.join(save_folder, selected_zip_file)

                        # Define the list of files to delete
                        files_to_delete = [
                                        '1_fog_level_ru_03_01.cfg',
                                        '1_fog_level_ru_04_01.cfg',
                                        '1_fog_level_ru_05_01.cfg',
                                        '1_fog_level_ru_08_01.cfg',
                                        '1_fog_level_us_01_01.cfg',
                                        '1_fog_level_us_01_02.cfg',
                                        '1_fog_level_us_01_03.cfg',
                                        '1_fog_level_us_01_04_new.cfg',
                                        '1_fog_level_us_02_01.cfg',
                                        '1_fog_level_us_03_01.cfg',
                                        '1_fog_level_us_04_01.cfg',
                                        '1_fog_level_us_06_01.cfg',
                                        '1_fog_level_us_07_01.cfg',
                                        '1_fog_level_us_09_01.cfg',
                                        '1_fog_level_us_10_01.cfg',
                                        '1_fog_level_us_11_01.cfg',
                                        '1_sts_level_us_01_01.cfg',
                                        '1_sts_level_us_01_02.cfg',
                                        '1_sts_level_us_01_03.cfg',
                                        '1_sts_level_us_01_04_new.cfg',
                                        '1_sts_level_us_02_01.cfg',
                                        'CompleteSave.cfg',
                                        'CompleteSave1.cfg',
                                        'CompleteSave2.cfg',
                                        'CompleteSave3.cfg',
                                        'CommonSslSave.cfg,',
                                        'fog_level_ru_02_02.cfg',
                                        'fog_level_ru_03_01.cfg',
                                        'fog_level_ru_04_01.cfg',
                                        'fog_level_ru_05_01.cfg',
                                        'fog_level_ru_08_01.cfg',
                                        'fog_level_us_01_01.cfg',
                                        'fog_level_us_02_01.cfg',
                                        'fog_level_us_03_01.cfg',
                                        'fog_level_us_04_01.cfg',
                                        'fog_level_us_06_01.cfg',
                                        'fog_level_us_07_01.cfg',
                                        'fog_level_us_09_01.cfg',
                                        'sts_level_us_01_01.cfg',
                                    ]
                        # Download and unzip the selected file
                        download_and_unzip_file(vps_creds['hostname'], vps_creds['port'], vps_username, vps_password, folder_path, selected_zip_file, local_path, save_folder, files_to_delete)



                    else:
                        print(Fore.RED + "No folders or files found on the server")



                elif operation == 'U':
                    # Define the list of files to zip
                    files_to_zip = [
                        '1_fog_level_ru_02_02.cfg',
                        '1_fog_level_ru_03_01.cfg',
                        '1_fog_level_ru_04_01.cfg',
                        '1_fog_level_ru_05_01.cfg',
                        '1_fog_level_ru_08_01.cfg',
                        '1_fog_level_us_01_01.cfg',
                        '1_fog_level_us_01_02.cfg',
                        '1_fog_level_us_01_03.cfg',
                        '1_fog_level_us_01_04_new.cfg',
                        '1_fog_level_us_02_01.cfg',
                        '1_fog_level_us_03_01.cfg',
                        '1_fog_level_us_04_01.cfg',
                        '1_fog_level_us_06_01.cfg',
                        '1_fog_level_us_07_01.cfg',
                        '1_fog_level_us_09_01.cfg',
                        '1_fog_level_us_10_01.cfg',
                        '1_fog_level_us_11_01.cfg',
                        '1_sts_level_us_01_01.cfg',
                        '1_sts_level_us_01_02.cfg',
                        '1_sts_level_us_01_03.cfg',
                        '1_sts_level_us_01_04_new.cfg',
                        '1_sts_level_us_02_01.cfg',
                        'CompleteSave.cfg',
                        'CompleteSave1.cfg',
                        'CompleteSave2.cfg',
                        'CompleteSave3.cfg',
                        'CommonSslSave.cfg,',
                        'fog_level_ru_02_02.cfg',
                        'fog_level_ru_03_01.cfg',
                        'fog_level_ru_04_01.cfg',
                        'fog_level_ru_05_01.cfg',
                        'fog_level_ru_08_01.cfg',
                        'fog_level_us_01_01.cfg',
                        'fog_level_us_02_01.cfg',
                        'fog_level_us_03_01.cfg',
                        'fog_level_us_04_01.cfg',
                        'fog_level_us_06_01.cfg',
                        'fog_level_us_07_01.cfg',
                        'fog_level_us_09_01.cfg',
                        'sts_level_us_01_01.cfg',
                    ]

                    # Define paths
                    local_zip_path = os.path.join(save_folder)
                    os.makedirs(local_zip_path, exist_ok=True)

                    # Create the ZIP archive and get the filename
                    zip_filename = create_zip_archive(save_folder, files_to_zip, local_zip_path, steam_username)

                    # Get the remote path
                    remote_zip_path = get_remote_zip_path(vps_username, steam_username, steamid64)


                    # Upload the ZIP archive to the VPS and check the status
                    remote_file_path = f'{remote_zip_path}/{zip_filename}'
                    upload_status = upload_to_vps(os.path.join(local_zip_path, zip_filename), remote_file_path, vps_hostname, vps_port, vps_username, vps_password)


                    # Remove the local ZIP archive if the upload was successful
                    if upload_status:
                        os.remove(os.path.join(local_zip_path, zip_filename))

                    # Print a message based on the upload status
                    if upload_status:
                        print(Fore.GREEN + f"Upload completed successfully: {zip_filename} to {remote_zip_path}")
                    else:
                        print(Fore.RED + f"Upload failed: {zip_filename} to {remote_zip_path}")
                        os.remove(os.path.join(local_zip_path, zip_filename))

                else:
                    print(Fore.RED + "Invalid operation. Exiting...")
            else:
                print("Some or all required files are missing.")
        else:
            print("No SnowRunner save folders found.")
    else:
        print("Steam folder not found.")


if __name__ == "__main__":
    main()
    input(Fore.LIGHTYELLOW_EX + "Press Enter to exit...")
