# µLearn Backend Project

## Project Setup

### Clone the Project
Clone the repository to your local machine using the following command:

```commandline
git clone <repo-url>
```

### Create the virtual environment
Create a virtual environment in a venv folder and activate it:
```bash
python -m venv venv
source venv/bin/activate
```
for windows:
```bash
python -m venv venv
venv\Scripts\activate.bat  
```
### Install Dependencies
Install the required dependencies using the following command:
```commandline
pip install -r requirements.txt
```

### Set environment variables
Create a .env file in the project root directory by copying .env.sample and replace with your values.

### Run the Project
```commandline
python manage.py runserver
```

Now the project is up and running on http://localhost:8000/.
