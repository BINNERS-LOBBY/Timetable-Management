# Timetable Generator

## Overview

A web-based timetable generation system for educational institutions built with Flask. The application allows administrators to create automated class schedules by configuring classes, subjects, faculty members, and their assignments. The system uses intelligent algorithms to distribute faculty workload while handling constraints like lab blocks and faculty availability. Features include a multi-step configuration wizard, automated timetable generation with conflict resolution, and an edit mode for manual adjustments.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Template Engine**: Jinja2 templates with Flask for server-side rendering
- **Multi-step Wizard**: Progressive configuration flow through 5 distinct steps
- **Interactive UI**: JavaScript-enhanced forms for dynamic subject/faculty management
- **Visual Feedback**: Color-coded timetable cells indicating labs, conflicts, and edits
- **Edit Mode**: In-place editing capabilities with visual indicators for modified cells

### Backend Architecture
- **Web Framework**: Flask with session-based state management
- **Algorithm Design**: Custom scheduling algorithm with constraint satisfaction
- **Faculty Assignment**: Intelligent workload distribution with availability checking
- **Lab Scheduling**: Block scheduling for consecutive period requirements
- **Conflict Resolution**: Automated handling of faculty conflicts and workload limits

### Data Management
- **Session Storage**: Flask sessions for multi-step form data persistence
- **In-Memory Processing**: Transient data structures for timetable generation
- **JSON Serialization**: Client-server data exchange for complex form inputs
- **No Database**: Stateless application design without persistent storage

### Scheduling Algorithm
- **Constraint Satisfaction**: Faculty availability and workload limit enforcement
- **Random Selection**: Balanced assignment among eligible faculty members
- **Block Allocation**: Consecutive slot finding for laboratory sessions
- **Conflict Detection**: Real-time validation of scheduling conflicts
- **Load Balancing**: Even distribution of teaching loads across faculty

## External Dependencies

### Core Framework
- **Flask**: Web application framework and routing
- **Jinja2**: Template rendering engine (bundled with Flask)

### Python Standard Library
- **os**: Environment variable access for configuration
- **logging**: Debug and error tracking
- **random**: Algorithm randomization for fair assignment
- **json**: Data serialization for form processing

### Frontend Assets
- **CSS Grid/Flexbox**: Modern layout system for responsive design
- **Vanilla JavaScript**: Form validation and dynamic content management
- **No External CDNs**: Self-contained styling and scripting

### Development Environment
- **Session Management**: Flask's built-in session handling
- **Debug Mode**: Development server with hot reloading
- **Environment Variables**: Configuration through SESSION_SECRET