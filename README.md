# All daily life automation script.
## 1) NIT Rourkela Network Login Automation Script (nitrkl_10hr_autologin.py)
The purpose of the above script is to be automating the login process to the NIT Rourkela Login portal using the Selenium and BeautifulSoup libraries in Python. The script is designed to repeatedly attempt the login at regular intervals (__default 10 Hrs__) and print whether the login was successful or not. The script can use prevent the ANYDESK disconnection issue due to automatic logout from NIT RKL network(__specially Remote Desktop provided for research for BTECH/ MTech/ PhD__).
### Installation Instructions

#### 1. Clone the Repository or Download it directly
```bash
git clone https://github.com/bishwajitprasadgond/automation_script.git
```
#### 2. Install Dependencies
Make sure you have Python installed. The script relies on the following Python packages:

- selenium
- beautifulsoup4
```bash
pip install selenium beautifulsoup4
```

#### 3. Environment
- Operating System: Any
- Browser: Microsoft Edge (Chromium-based)
- Python Version: 3.x
  
###  How to Run
#### 1. Configure Script:
Open the script and provide your __username__ and __password__ in the main function.
#### 2. Run the Script:
```bash
python nitrkl_10hr_autologin.py
```
This will execute the script, perform the login, and display the success or failure message.

#### 3. Wait for Next Attempt:
After each login attempt, the script will wait for 10 hours before the next attempt.

Here's a README file you can use to explain the file organization function implemented in the Python script:

---

## 2) File Organization Script

### Overview

This Python script organizes files in a specified folder based on their file extensions. It creates a folder for each unique file extension found in the folder and moves files into their respective folders based on their extensions.

### Usage

1. Ensure you have Python installed on your system.
2. Modify the `folder_location` variable in the script to point to the folder you want to organize.
3. Run the script using a Python interpreter.

### Example

Suppose you have a folder named `my_folder` with the following files:

- `file1.txt`
- `file2.txt`
- `image1.png`
- `image2.jpg`

After running the script, the folder structure will be:

```
my_folder/
|____ txt/
|     |____ file1.txt
|     |____ file2.txt
|
|____ png/
|     |____ image1.png
|
|____ jpg/
      |____ image2.jpg
```

### Note

- Folders without file extensions will be left untouched.
- If a file with a particular extension already exists in the destination folder, it will not be moved, and an error message will be printed.

---


