from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class Subject(db.Model):
    """Store commonly used subjects for auto-completion"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    default_periods = db.Column(db.Integer, default=0)
    default_type = db.Column(db.String(20), default='theory')  # theory or lab
    default_lab_block = db.Column(db.Integer, default=0)
    usage_count = db.Column(db.Integer, default=0)  # Track popularity
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'default_periods': self.default_periods,
            'default_type': self.default_type,
            'default_lab_block': self.default_lab_block,
            'usage_count': self.usage_count
        }

class SavedTimetable(db.Model):
    """Store generated timetables for reuse"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    configuration = db.Column(db.Text, nullable=False)  # JSON of all settings
    schedule_data = db.Column(db.Text, nullable=False)  # JSON of generated schedule
    faculty_view_data = db.Column(db.Text, nullable=False)  # JSON of faculty schedules
    load_summary_data = db.Column(db.Text, nullable=False)  # JSON of load summary
    warnings_data = db.Column(db.Text, default='[]')  # JSON of warnings
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used = db.Column(db.DateTime, default=datetime.utcnow)
    usage_count = db.Column(db.Integer, default=0)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'configuration': json.loads(self.configuration) if self.configuration else {},
            'schedule_data': json.loads(self.schedule_data) if self.schedule_data else {},
            'faculty_view_data': json.loads(self.faculty_view_data) if self.faculty_view_data else {},
            'load_summary_data': json.loads(self.load_summary_data) if self.load_summary_data else [],
            'warnings_data': json.loads(self.warnings_data) if self.warnings_data else [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_used': self.last_used.isoformat() if self.last_used else None,
            'usage_count': self.usage_count
        }
    
    @classmethod
    def save_timetable(cls, name, description, session_data, schedule, faculty_view, load_summary, warnings):
        """Save a complete timetable configuration and results"""
        timetable = cls(
            name=name,
            description=description,
            configuration=json.dumps({
                'class_names': session_data.get('class_names', []),
                'subjects_per_class': session_data.get('subjects_per_class', {}),
                'faculties': session_data.get('faculties', []),
                'faculty_classes': session_data.get('faculty_classes', {}),
                'periods_per_day': session_data.get('periods_per_day', 6),
                'workload_limit': session_data.get('workload_limit', 28),
                'edited_cells': session_data.get('edited_cells', {})
            }),
            schedule_data=json.dumps(schedule),
            faculty_view_data=json.dumps(faculty_view),
            load_summary_data=json.dumps(load_summary),
            warnings_data=json.dumps(warnings)
        )
        db.session.add(timetable)
        db.session.commit()
        return timetable

class Faculty(db.Model):
    """Store faculty information for reuse"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120))
    department = db.Column(db.String(100))
    subjects = db.Column(db.Text)  # JSON list of subjects they can teach
    max_workload = db.Column(db.Integer, default=28)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    active = db.Column(db.Boolean, default=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'department': self.department,
            'subjects': json.loads(self.subjects) if self.subjects else [],
            'max_workload': self.max_workload,
            'active': self.active
        }