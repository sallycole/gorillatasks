
# Curriculum Manager

A web-based curriculum management system that helps users track and manage their learning progress across multiple courses and subjects. The platform allows educators to create structured learning paths and enables students to follow their progress, manage tasks, and maintain consistent study habits.

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
  - Role-based access (students and curriculum creators)

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

### For Educators
1. Create an account
2. Create a new curriculum
3. Add tasks with descriptions and resources
4. Publish the curriculum for students

### For Students
1. Browse available curriculums
2. Enroll in desired courses
3. Set study goals and target completion dates
4. Track progress through the dashboard

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

## Support

For support, questions, or feedback, please contact: sallycole@gmail.com

## Screenshots

Key features demonstrated in the screenshots:
1. Dashboard with progress tracking
2. Curriculum creation interface
3. Task management system
4. Weekly goal visualization
5. Archive view of completed curriculums

## Future Roadmap

Upcoming Features:
- AI-powered motivation system featuring an engaging gorilla character
- Personalized student encouragement based on learning patterns
- Real-time motivation messages using the latest educational psychology research
- Adaptive feedback system to maintain student engagement
- Integration with existing task completion tracking

