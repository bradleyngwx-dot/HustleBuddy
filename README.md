# HustleBuddy
HustleBuddy is a Django app for student freelancers and home-based businesses to manage clients, appointments, payments, time logs, and dashboard metrics.

## Live Demo

[View HustleBuddy on Render](https://hustlebuddy.onrender.com/)

*Note: The Render app may take a short while to load if the server is idle.*

### Features
- Client management
- Appointment scheduling
- Automatic payment records from priced appointments
- Payment tracking: pending, paid, overdue
- Time logs from completed appointments
- Dashboard summaries and charts
- Email-based auth via django-allauth

### Tech Stack
- **Backend**: Python, Django, Django ORM
- **Frontend**: Django Templates, HTML, CSS, Vanilla JavaScript
- **Charts**: Chart.js
- **Authentication**: django-allauth
- **Database**: PostgreSQL, SQLite for local testing
- **Static Files**: Django staticfiles, WhiteNoise
- **Deployment**: Docker, Gunicorn, Render
- **Local Development**: Docker Compose, .env files, python-dotenv
- **Testing**: Django TestCase

## Setup Instructions 
__To run the app locally, follow these steps:__
### For Local Development
```
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py runserver
```
For signup and password reset testing, emails are printed in the terminal where `python manage.py runserver` is running. Copy the verification or reset link from the terminal output and open it in your browser.

Your personal `.env` can use Gmail SMTP if you want real emails locally, but `.env.example` is configured for easier tester setup.

### For Docker + PostgreSQL Local Setup
Tester only needs to install Docker.
1. Copy the environment file:
```
Copy-Item .env.example .env
```
2. In the .env file, set the following environment variables:
- USE_SQLITE=False
- DB_HOST=db
- DB_NAME=hustlebuddy
- DB_USER=postgres
- DB_PASSWORD=postgres
- DB_PORT=5432
3. Start the Docker containers:

```
docker compose up --build
```
4. Run migrations:
```
docker compose exec web python manage.py migrate
```

5. Access the app at 
```text
http://127.0.0.1:8000/
```
For signup and password reset testing, emails are printed in the Docker `web` container logs. If needed, view them with:

```
docker compose logs web
```

### NOTE: If you want to test real email sending with Gmail SMTP, update `.env` with your own Gmail details:

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-gmail-app-password
DEFAULT_FROM_EMAIL=your-email@gmail.com
```
## Testing
To run the tests, use the following command:
```
python manage.py test
```

### Future Improvements
- Splashdown: Email Reminders for upcoming appointments

## Team
- Yeo Yirong Justin
- Ng Wei Xun Bradley