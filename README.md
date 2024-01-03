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

