# Job Marketplace Platform - Full Upwork Clone

## Overview
A comprehensive Flask-based freelance marketplace platform modeled after Upwork. Features complete user profiles, advanced proposal system, messaging, reviews, job categories, wallet tracking, notifications, and professional Upwork-inspired design.

**Current Status**: Full-featured Upwork clone with core functionality implemented
**Last Updated**: November 23, 2025

## Recent Changes
- **November 23, 2025 - Major Update**: Expanded to full Upwork clone
  - **Database Schema**: Complete overhaul with 10+ tables (profiles, proposals, contracts, messages, reviews, categories, transactions, notifications)
  - **User Profiles**: Added comprehensive profiles with title, bio, skills, hourly rate, location, ratings, total earnings, job count
  - **Proposal System**: Enhanced from simple applications to full proposals with cover letters, bid amounts, delivery time
  - **Messaging**: Real-time messaging system between clients and freelancers
  - **Reviews & Ratings**: 5-star review system with comments, automatic profile rating updates
  - **Job Categories**: 8 predefined categories (Web Dev, Mobile, Design, Writing, Marketing, Data Entry, Customer Service, Accounting)
  - **Search & Filters**: Advanced job search by keywords and categories
  - **Contracts**: Contract management system linking accepted proposals to ongoing work
  - **Wallet**: Balance tracking interface (UI ready, payment integration pending)
  - **Notifications**: System notifications for proposals, messages, contracts
  - **Upwork Design**: Complete UI/UX redesign matching Upwork's green color scheme and professional layout
- Configured Flask workflow on port 5000

## Project Architecture

### Technology Stack
- **Backend**: Flask (Python 3.11)
- **Database**: SQLite with proper foreign key relationships
- **Session Management**: Flask-Session with filesystem storage
- **Security**: Werkzeug password hashing
- **Frontend**: Jinja2 templates with custom CSS

### File Structure
```
/
├── app.py                  # Main Flask application with all routes
├── database.py            # Database schema and helper functions
├── marketplace.db         # SQLite database (auto-generated)
├── templates/             # HTML templates
│   ├── base.html         # Base template with navigation
│   ├── index.html        # Home page
│   ├── register.html     # User registration
│   ├── login.html        # User login
│   ├── client_dashboard.html      # Client's posted jobs
│   ├── post_job.html              # Job posting form
│   ├── freelancer_dashboard.html  # Freelancer's applications
│   └── browse_jobs.html           # Browse available jobs
├── static/css/
│   └── style.css         # All styling and responsive design
└── flask_session/        # Session storage (auto-generated)
```

### Database Schema

**users table**:
- id (PRIMARY KEY)
- username (UNIQUE)
- password (hashed)
- role (client or freelancer)
- created_at (timestamp)

**jobs table**:
- id (PRIMARY KEY)
- title
- description
- client_id (FOREIGN KEY → users.id)
- created_at (timestamp)

**applications table**:
- id (PRIMARY KEY)
- job_id (FOREIGN KEY → jobs.id)
- freelancer_id (FOREIGN KEY → users.id)
- applied_at (timestamp)
- UNIQUE constraint on (job_id, freelancer_id)

## Features

### Authentication System
- User registration with username, password, and role selection
- Password hashing using Werkzeug
- Session-based login persistence
- Logout functionality

### Client Features
- Post new jobs with title and description
- View all posted jobs on dashboard
- See number of applicants per job
- View detailed list of applicants with usernames and application dates

### Freelancer Features
- Browse all available jobs
- Apply to jobs with one click
- View application status (already applied vs available)
- Dashboard showing all jobs applied to
- Cannot apply to same job twice

### User Experience
- **Upwork-inspired design** with professional green color scheme
- Clean white card-based layouts with subtle borders
- Sticky top navigation bar with role-aware menu items
- Modern rounded buttons and form inputs
- Responsive design optimized for mobile and desktop
- Elegant flash messages for user feedback
- Professional typography and spacing
- Empty state messages with clear calls-to-action
- Hero sections with gradient backgrounds

## Environment Variables
- `SESSION_SECRET`: Secret key for session management (configured in Replit Secrets)

## Running the Application
The app runs automatically via the configured workflow:
- Command: `python app.py`
- Port: 5000
- The database is initialized automatically on first run

## User Preferences
None documented yet.

## Next Phase Ideas
- Job editing and deletion for clients
- Application status tracking (pending, accepted, rejected)
- User profiles with skills and experience
- Messaging system between clients and freelancers
- Search and filter functionality for jobs
- Job categories and tags
- File attachments for job posts
- Rating and review system
