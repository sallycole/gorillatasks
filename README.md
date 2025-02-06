
# Gorilla Tasks

Frustrated with slow learning progress? Gorilla Tasks accelerates student learning with a web-based curriculum management system built for efficiency. It transforms any curriculum—whether a custom collection of online resources or an existing course sequence—into a set of easily accomplishable tasks: read, watch, listen, or do. Upon enrolling in a curriculum, students select their desired finish date and study days per week, and Gorilla Tasks automatically calculates and dynamically updates daily and weekly goals to maintain an optimal pace for on-time completion.  Real-time progress tracking visualizes completed and skipped tasks, allowing students to archive finished work or reactivate past tasks from the archive as needed.

## Disclaimer

This project was created with a heavy reliance on AI tools including Cursor AI, Chat GPT, Replit Assistant, and Replit Agent. It is a proof of concept for a learning management system capable of making homeschooling more efficient and effective.

## Live Demo

Try out Gorilla Tasks at [https://gorilla-tasks.replit.app/](https://gorilla-tasks.replit.app/)

## Features

- **Curriculum Creation & Management**
  - Create and publish educational curriculums
  - Add structured tasks with various action types (Read, Watch, Listen, Do)
  - Support for different grade levels
  - XML-based curriculum import

- **Student Progress Tracking**
  - Track task completion and study time
  - Weekly goals and progress monitoring
  - Automated task scheduling based on target completion dates
  - Archive completed curriculums

- **User Management**
  - User registration and authentication
  - Customizable user profiles
  - Time zone support for accurate progress tracking
  - Role-based access (users and superusers)

- **Real-time Updates**
  - WebSocket integration for live progress updates
  - Instant task status changes

## Technologies Used

- **Backend**
  - Python 3.11
  - Flask
  - Flask-SocketIO
  - SQLAlchemy
  - PostgreSQL

- **Frontend**
  - HTML5
  - Bootstrap (Dark Theme)
  - JavaScript
  - WebSocket

- **Package Management**
  - pip (Python packages)

## Installation & Setup

1. Clone the repository in Replit
2. Install dependencies:
```sh
pip install -r requirements.txt
```

3. Configure environment variables:
- Set up a PostgreSQL database
- Configure `DATABASE_URL`
- Set `FLASK_SECRET_KEY`

4. Initialize the database:
```sh
python migrations.py
```

5. Run the application:
```sh
python main.py
```

## Usage

### For Users
1. Create an account
2. Create any number of private curriculums
3. Browse public curriculums
4. Enroll in any number of private or public curriculums
5. Set study goals and target completion dates
6. Visit the study dashboard, which shows the next 10 tasks to complete for each and every enrolled curriculum as well as the daily task and weekly tasks to complete for each curriculum
7. Press start when a task is started and finish when a task is finished. If a task has an associated URL, it will automatically launch when the user clicks the start button. 

### For Superusers
1. Set superuser status in the database for the most trusted users
2. Superusers have all the features that users have along with the ability to publish curriculums they have contributed
3. Only superusers can make public curriculums

## Configuration

Required environment variables:
- `DATABASE_URL`: PostgreSQL connection string
- `FLASK_SECRET_KEY`: Secret key for session management
- `FLASK_ENV`: Development/Production environment

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

Guidelines:
- Follow PEP 8 style guide for Python code
- Write meaningful commit messages
- Add tests for new features
- Update documentation as needed

## License

This is free and unencumbered software released into the public domain.

Anyone is free to copy, modify, publish, use, compile, sell, or distribute this software, either in source code form or as a compiled binary, for any purpose, commercial or non-commercial, and by any means.

For more information, please refer to <http://unlicense.org/>

## Credits

This project uses several open-source libraries:
- Flask
- SQLAlchemy
- Flask-SocketIO
- Bootstrap
- Feather Icons

## Screenshots

Key features demonstrated in the screenshots:

### Dashboard with Progress Tracking
![Dashboard showing task progress and goals](static/images/dashboard%20with%20progress%20tracking.png)

### Curriculum Creation Interface
![Interface for creating new curriculums](static/images/curriculum%20creation%20interface.png)

### Task Editing Interface
![Interface for editing curriculum tasks](static/images/task%20editing%20interface.png)

### Curriculum Browsing and Sorting
![Browse and sort available curriculums](static/images/curriculum%20browsing%20and%20sorting%20interface.png)

### Archive View
![View of archived enrollments](static/images/archive%20view.png)

### Progress Reporting
![Detailed progress reporting](static/images/progress%20report.png)

## Future Roadmap

Upcoming Features:
- AI-powered motivation system featuring an engaging gorilla character