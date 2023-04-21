# Flask Music Directory Application Hosted on Amazon Web Services 
This is a Flask application where users can create an account, view a directory of selected songs, search through them, and subscribe to their preferred songs.
It is currently hosted on an EC2 Instance on AWS. This repository just contains the source code.
Running the application locally is not possible unless connected to AWS however the code to run is shown below.
```
python3 -m venv <name of environment>

. <name of environment>/bin/activate

python3 -m flask run
```