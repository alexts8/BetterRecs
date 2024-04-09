**Alexandros Tsiogas C20336236 - Final Year Project **

**Important!** 
This application requires a Spotify acount to run correctly.
If you would like to log in with your own Spotify account, the account's email address needs to be added to 
an application whitelist. Please feel free to contact me with your email and
I will add you to this whitelist, allowing you to log in with your own Spotify account.
Otherwise, please use this dummy account - USERNAME: alextsiogas.fyp@gmail.com   PASSWORD: alexfyp2024
Please be aware that this account doesnt have a significatnt Spotify listening histore, and so the "Profile" page
may not display much data.

Please also note that the application may face difficulties running in eduroam/public WIFI connections,
due to their network restrictions. Please use a personal WIFI connection.

This application was developed and tested in Visual Studio Code. These steps will describe how to run
the applcation in VSCode.

**Running The App**
Once this folder has been extracted, open it in an editor in VSCode. The python file "betterrecs.py" 
should be ran, using the "Run Code" button in the top right of the screen. A link to a localhost URL (should be http://127.0.0.1:5000)
will display in the terminal - when followed, this link should display the Spotify Authentication page.
Log in using any Spotify account, and you should access the application.

If the app doesn't run on first attempt, certain packages may need to be installed
(flask, spotipy, etc) - the following commands can be used to download the necessary packages

!pip install flask
!pip install spotipy
!pip install pandas
!pip install scikit-learn

Please contact me if any other issues are encountered running the application.

