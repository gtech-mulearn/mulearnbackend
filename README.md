
# µLearn Backend Project

Backend service for the µLearn platform.

---

## 🧰 Requirements (Install these first)

Make sure these tools are installed before setting up the project.

### 1️⃣ Install Git  
Download: https://git-scm.com/downloads

Verify installation:
```bash
git --version
````

---

### 2️⃣ Install Python 3.10

Download Python 3.10 from:
[https://www.python.org/downloads/release/python-3100/](https://www.python.org/downloads/release/python-3100/)

During installation, make sure you tick:

```
✅ Add Python to PATH
```

Verify installation:

```bash
python --version
```

---

## 🚀 Project Setup

### 1️⃣ Clone the Repository

```bash
git clone <repo-url>
cd <project-folder>
```

---

### 2️⃣ Create Virtual Environment

#### Windows (PowerShell)

```bash
python -m venv venv
.\venv\Scripts\Activate.ps1
```


If activation is successful, you will see:

```
(venv)
```

in the terminal.

---

### 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 4️⃣ Set Environment Variables

Create a `.env` file in the project root directory.

Copy the contents from:

```
.env.sample
```

Then replace the values with your own configuration.

---

### 5️⃣ Apply Required Migration Script

Apply the migration before running the project:

👉 [https://gist.github.com/e3ob/9e1116996e1daec8df8701548eeaa528](https://gist.github.com/e3ob/9e1116996e1daec8df8701548eeaa528)

---

### 6️⃣ Create Required Folders

Before starting the server, create the logs directory.

#### Windows

```bash
mkdir logs
```

---

### 7️⃣ Run the Server

```bash
python manage.py runserver
```

The project will start at:

```
http://localhost:8000/
```

