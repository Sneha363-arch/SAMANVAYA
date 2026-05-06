# Samanvaya

A full-stack system that enables seamless data synchronization between two independent government systems. The application ensures consistent data flow, real-time updates, and visibility across systems through a unified interface.

---

## 🚀 Tech Stack

* **Backend:** FastAPI (Python)
* **Database:** PostgreSQL
* **Frontend:** HTML, CSS, JavaScript
* **Containerization:** Docker & Docker Compose

---

## 📁 Project Structure

```
project-root/
│
├── backend/
├── frontend/
├── docker-compose.yml
├── .env.example
├── README.md
```

---

## ⚙️ Setup & Run (Docker — Recommended)

### 1. Clone the repository

```
git clone <your-repo-url>
cd <project-folder>
```

---

### 2. Create environment file

Copy the example file:

```
cp .env.example .env
```

Update values if required.

---

### 3. Start the application

```
docker compose up --build
```

---

### 4. Access the application

* **Frontend:** http://localhost:3000
* **Backend API:** http://localhost:8000
* **API Docs:** http://localhost:8000/docs

---

## 🛠️ Run Locally (Without Docker)

### 1. Setup database

Ensure PostgreSQL is running and create a database.

---

### 2. Run backend

```
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

---

### 3. Run frontend

Open the frontend directly in browser:

```
frontend/index.html
```

---

## 🧪 Basic Testing

### Create a record

```
curl -X POST http://localhost:8000/sws/update \
  -H "Content-Type: application/json" \
  -d '{
    "sws_application_id": "SWS-001",
    "business_legal_name": "Example Company",
    "registered_address": "Sample Address",
    "authorized_signatory_name": "John Doe",
    "business_type": "Manufacturing"
  }'
```

---

### Fetch records

```
curl http://localhost:8000/sws/all
curl http://localhost:8000/fds/all
```

---

## 📌 Notes

* Environment files (`.env`, `.env.local`) are not included in the repository
* Use `.env.example` as a reference
* Ensure Docker is installed before running containers

---

## 📄 License

This project is for educational and demonstration purposes.
