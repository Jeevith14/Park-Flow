# ParkFlow – Smart Parking Manager

> **Academic Data Structures & Algorithms Project (Python / Flask / PostgreSQL / Vercel)**  
> A full-stack, responsive parking management web application utilizing a **Python Stack (LIFO: Last-In, First-Out)** data structure to allocate and release 20 parking bays.  
>  
> **Live Production URL:** [https://park-flow-nu.vercel.app](https://park-flow-nu.vercel.app)  
> **GitHub Repository:** [https://github.com/Jeevith14/Park-Flow](https://github.com/Jeevith14/Park-Flow)

---

## 1. Project Overview & Architecture

**ParkFlow** is a modern, real-time parking slot management application built specifically for academic demonstrations, viva examinations, and production deployment on **Vercel** with **PostgreSQL (Neon / Vercel Postgres)**.

### Architectural Principle
* **Data Structure in Python**: Core slot allocation and release logic resides strictly on the backend in pure Python (`ParkingStack` class), not in client-side JavaScript.
* **LIFO Allocation Principle**:
  * The available slots are managed in a Stack.
  * When a vehicle enters, `stack.pop()` allocates the slot currently at the **TOP** of the stack.
  * When a vehicle departs, `stack.push(slot)` pushes that freed slot back to the **TOP**.
  * Consequently, the most recently freed bay is re-allocated first, minimizing driver search time and matching real-world parking efficiency.
* **Persistent Dual-Engine Storage**:
  * **Production (Vercel Serverless)**: Neon PostgreSQL or Vercel Postgres via `DATABASE_URL`.
  * **Local Development**: Automatic fallback to local SQLite (`parkflow.db`) with zero setup required.
* **Vercel Serverless Compatible**: Fully configured with `api/index.py` and `vercel.json` rewrites.

---

## 2. Python Stack (LIFO) Academic Deep-Dive & Viva Guide

### Stack Operations Table
| Operation | Python Implementation | Academic Definition | Time Complexity | ParkFlow Role |
| :--- | :--- | :--- | :--- | :--- |
| **`push(slot)`** | `self._slots.append(slot)` | Adds an element to the top | $\mathcal{O}(1)$ | Returns a vacated slot to the top when a vehicle exits. |
| **`pop()`** | `self._slots.pop()` | Removes and returns the top element | $\mathcal{O}(1)$ | Allocates the top available bay when a vehicle enters. |
| **`peek()`** | `self._slots[-1]` | Inspects the top element without removing | $\mathcal{O}(1)$ | Displays the next slot that will be assigned on the dashboard. |
| **`is_empty()`** | `len(self._slots) == 0` | Checks if stack has 0 elements | $\mathcal{O}(1)$ | Detects when all 20 bays are occupied (prevents underflow). |
| **`size()`** | `len(self._slots)` | Returns count of items | $\mathcal{O}(1)$ | Computes available bays remaining. |

### Viva Examination Q&A
1. **Q: Why use a Stack instead of a Queue for parking bays?**
   * *Answer*: In physical multi-story or outdoor lots, bays vacated closest to the entrance or exit ramp are ideal for immediate re-use. Directing the incoming vehicle into the most recently vacated slot (LIFO) ensures optimal turnaround and reduces circulation congestion.
2. **Q: How does Python achieve $\mathcal{O}(1)$ push and pop?**
   * *Answer*: Python lists are dynamic arrays. Adding an item to the end (`append()`) and removing from the end (`pop()`) are amortized $\mathcal{O}(1)$ operations because no element shifts are needed.
3. **Q: How does ParkFlow prevent Stack Underflow and Overflow?**
   * *Answer*: Before every `pop()`, `is_empty()` checks if any slots remain. If empty, it returns an HTTP 400 error ("Parking lot is full"). Before `push()`, boundary checks guarantee the slot number is between 1 and 20 and not already in the stack.

---

## 3. Project Directory Structure

```text
parkflow/
├── api/
│   └── index.py                # Vercel serverless WSGI entrypoint
├── data_structures/
│   ├── __init__.py             # Package initializer
│   └── parking_stack.py        # Hand-crafted ParkingStack class (LIFO)
├── static/
│   ├── css/
│   │   └── style.css           # Responsive dashboard design system
│   └── js/
│       └── app.js              # RESTful API client controller
├── templates/
│   └── index.html              # Responsive single-page application dashboard
├── tests/
│   ├── test_stack.py           # Unit tests for Python ParkingStack
│   ├── test_database.py        # Tests for dual-engine database persistence
│   └── test_api.py             # End-to-end integration test suite (9 test cases)
├── app.py                      # Flask web application & REST API routes
├── database.py                 # Dual-engine adapter (PostgreSQL + SQLite)
├── services.py                 # Service layer orchestrating stack & persistence
├── init_db.py                  # Standalone database initialization script
├── run.py                      # Local development server runner
├── vercel.json                 # Vercel deployment routing configuration
├── requirements.txt            # Python dependencies
├── .env.example                # Sample environment configuration
└── README.md                   # Complete academic documentation
```

---

## 4. Local Installation & Running

### Prerequisites
* Python 3.9+ installed
* Git

### Step-by-Step Setup
1. **Clone or navigate to the directory**:
   ```bash
   cd C:\Users\jeevith\.gemini\antigravity\scratch\parkflow
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Initialize the database**:
   ```bash
   python init_db.py
   ```

4. **Start the local server**:
   ```bash
   python run.py
   ```
   Or:
   ```bash
   python app.py
   ```

5. **Open in browser**:
   Navigate to [http://127.0.0.1:5000](http://127.0.0.1:5000)

---

## 5. Running the Test Suite

Execute all 19 unit and integration tests:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

All 19 tests verify:
1. `ParkingStack` push, pop, peek, is_empty, size, underflow, and overflow.
2. Slot allocation and release cycles.
3. Duplicate vehicle number rejection.
4. Handling of full 20-slot lot capacity.
5. Persistent storage across serverless requests.
6. Search by vehicle plate and owner name.

---

## 6. Neon PostgreSQL Database Setup (Free)

For persistent cloud storage on Vercel:

1. Sign up for a free account at [neon.tech](https://neon.tech).
2. Click **Create Project** (e.g., name it `parkflow-db`).
3. Under the **Dashboard**, copy your **Connection String**:
   ```text
   postgresql://<username>:<password>@<ep-pooler-host>.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
4. Save this string — you will paste it as the `DATABASE_URL` environment variable in Vercel.

---

## 7. GitHub Upload Instructions

Initialize and push the repository to your GitHub account:

```bash
cd C:\Users\jeevith\.gemini\antigravity\scratch\parkflow

# 1. Initialize git
git init

# 2. Stage all files
git add .

# 3. Commit
git commit -m "Initial commit: ParkFlow Smart Parking Manager with Python Stack"

# 4. Create repository on GitHub (e.g. named 'parkflow') and link remote:
git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/parkflow.git

# 5. Push to GitHub
git branch -M main
git push -u origin main
```

---

## 8. Vercel Deployment Instructions

Deploy directly from your GitHub repository to Vercel in 3 simple steps:

### Step 1: Import Repository
1. Log in to [vercel.com](https://vercel.com).
2. Click **Add New...** → **Project**.
3. Select your GitHub repository (`parkflow`) and click **Import**.

### Step 2: Configure Environment Variables
In the **Environment Variables** section on the Vercel project configuration page, add:

| Key | Value | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | `postgresql://user:pass@ep-host.neon.tech/neondb?sslmode=require` | Your Neon PostgreSQL connection string |
| `SECRET_KEY` | *(Generate any random string)* | Flask session secret key |

*(Note: If you do not provide `DATABASE_URL`, ParkFlow will safely initialize with in-memory SQLite storage).*

### Step 3: Deploy
1. Keep the **Framework Preset** as **Other**.
2. Click **Deploy**.
3. Vercel will build the project and output your live production URL (e.g., `https://parkflow-smart-parking.vercel.app`).

---

## 9. RESTful API Reference

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/` | `GET` | Serves the main SPA Dashboard. |
| `/api/status` | `GET` | Returns lot statistics (total, available, occupied, utilization) & stack peek. |
| `/api/slots` | `GET` | Returns state of all 20 bays (bays 1–20) with vehicle info. |
| `/api/stack` | `GET` | Returns live Python ParkingStack elements, size, and viva notes. |
| `/api/vehicles` | `GET` | Returns list of currently parked vehicles. |
| `/api/park` | `POST` | Allocates next bay to incoming vehicle via `stack.pop()`. |
| `/api/exit` | `POST` | Processes departure and returns bay to stack via `stack.push(slot)`. |
| `/api/search?q=...` | `GET` | Searches vehicles by plate or owner name across active & history. |
| `/api/history` | `GET` | Returns complete audit log with durations and timestamps. |
| `/api/reset` | `POST` | Resets lot to initial 20 available bays. |
| `/api/health` | `GET` | Health check endpoint for deployment monitoring. |

---

## 10. License & Credits

Built for academic demonstration of fundamental computer science data structures.
Distributed under the MIT License.
