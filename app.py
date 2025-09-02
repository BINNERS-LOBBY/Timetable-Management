import os
import logging
from flask import Flask, render_template, request, redirect, url_for, session
import random
import json

# Configure logging for debugging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "fallback_secret_key_for_development")

DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

def choose_faculty_for_slot(subject, day_idx, period, faculties, slot_busy, load, limit):
    """Choose the best faculty for a given slot based on availability and workload"""
    eligible = [f for f in faculties if subject in f['subjects']]
    if not eligible:
        return None, False
    
    free_now = [f for f in eligible if f['name'] not in slot_busy.get((day_idx, period), set())]
    
    def pick_min_load(cands):
        if not cands:
            return None
        min_val = min(load.get(f['name'], 0) for f in cands)
        best = [f for f in cands if load.get(f['name'], 0) == min_val]
        return random.choice(best)
    
    under_limit_free = [f for f in free_now if load.get(f['name'], 0) < limit]
    if under_limit_free:
        chosen = pick_min_load(under_limit_free)
        return chosen['name'], False
    
    if free_now:
        chosen = pick_min_load(free_now)
        return chosen['name'], True
    
    return None, False

def find_block_slot_for_lab(class_schedule, periods_per_day, block_size):
    """Find available consecutive slots for lab blocks"""
    days = list(range(len(DAYS)))
    random.shuffle(days)
    
    for d in days:
        possible_starts = []
        for start in range(1, periods_per_day - block_size + 2):
            if all(not class_schedule.get((d, p)) for p in range(start, start + block_size)):
                possible_starts.append(start)
        
        random.shuffle(possible_starts)
        for s in possible_starts:
            return d, s
    
    return None, None

@app.route('/')
def home():
    """Home page redirects to step 1"""
    return redirect(url_for('step1'))

@app.route('/step1', methods=['GET', 'POST'])
def step1():
    """Step 1: Basic configuration"""
    if request.method == 'POST':
        try:
            session['num_classes'] = int(request.form['num_classes'])
            session['periods_per_day'] = int(request.form['periods_per_day'])
            session['workload_limit'] = int(request.form['workload_limit'])
            return redirect(url_for('step2_classes'))
        except (ValueError, KeyError) as e:
            return render_template('error.html', msg=f"Invalid input: {e}")
    
    return render_template('step1.html')

@app.route('/classes', methods=['GET', 'POST'])
def step2_classes():
    """Step 2: Class names configuration"""
    num = session.get('num_classes')
    if not num:
        return redirect(url_for('step1'))
    
    if request.method == 'POST':
        try:
            class_names = [request.form[f'class_name_{i}'] for i in range(1, num + 1)]
            # Filter out empty class names
            class_names = [name.strip() for name in class_names if name.strip()]
            if len(class_names) != num:
                return render_template('error.html', msg="All class names must be provided")
            session['class_names'] = class_names
            return redirect(url_for('step3_subjects'))
        except KeyError as e:
            return render_template('error.html', msg=f"Missing class name: {e}")
    
    return render_template('step2_classes.html', num=num)

@app.route('/subjects', methods=['GET', 'POST'])
def step3_subjects():
    """Step 3: Subjects configuration per class"""
    class_names = session.get('class_names')
    if not class_names:
        return redirect(url_for('step2_classes'))
    
    if request.method == 'POST':
        subjects_json = request.form.get('subjects_json', 'null')
        try:
            subjects_per_class = json.loads(subjects_json)
            # Validate and clean up subjects data
            for cname, subs in subjects_per_class.items():
                clean_subs = []
                for s in subs:
                    # Ensure required fields
                    name = s.get('name')
                    if not name:
                        continue
                    periods = int(s.get('periods', 0))
                    lab_block = int(s.get('lab_block') or 0)
                    typ = s.get('type', 'theory')
                    clean_subs.append({'name': name, 'periods': periods, 'lab_block': lab_block, 'type': typ})
                subjects_per_class[cname] = clean_subs
            session['subjects_per_class'] = subjects_per_class
            return redirect(url_for('step4_faculties'))
        except (json.JSONDecodeError, ValueError) as e:
            return render_template('error.html', msg=f'Invalid subjects data: {e}')
    
    return render_template('step3_subjects.html', class_names=class_names)

@app.route('/faculties', methods=['GET', 'POST'])
def step4_faculties():
    """Step 4: Faculty configuration"""
    class_names = session.get('class_names')
    subjects_per_class = session.get('subjects_per_class', {})
    if not class_names:
        return redirect(url_for('step2_classes'))
    
    # Extract unique subjects robustly (as a sorted list of names)
    unique_subjects = set()
    for subjects in subjects_per_class.values():
        for subject in subjects:
            if 'name' in subject and subject['name']:
                unique_subjects.add(subject['name'])
    unique_subjects = sorted(list(unique_subjects))
    
    if request.method == 'POST':
        faculties_json = request.form.get('faculties_json', 'null')
        try:
            faculties = json.loads(faculties_json)
            # Validate faculties: must have name and at least one subject
            clean_faculties = []
            for fac in faculties:
                name = fac.get('name')
                subjects = fac.get('subjects', [])
                if name and subjects:
                    clean_faculties.append({'name': name, 'subjects': subjects})
            session['faculties'] = clean_faculties
            return redirect(url_for('step5_faculty_classes'))
        except (json.JSONDecodeError, ValueError) as e:
            return render_template('error.html', msg='Invalid faculties data: ' + str(e))
    
    return render_template('step4_faculties.html', unique_subjects=unique_subjects)

@app.route('/faculty_classes', methods=['GET', 'POST'])
def step5_faculty_classes():
    """Step 5: Faculty-class assignment"""
    faculties = session.get('faculties')
    class_names = session.get('class_names')
    subjects_per_class = session.get('subjects_per_class', {})
    if not faculties or not class_names:
        return redirect(url_for('step1'))
    
    if request.method == 'POST':
        faculty_classes_json = request.form.get('faculty_classes_json', 'null')
        try:
            faculty_classes = json.loads(faculty_classes_json)
            session['faculty_classes'] = faculty_classes
            return redirect(url_for('generate'))
        except (json.JSONDecodeError, ValueError) as e:
            return render_template('error.html', msg='Invalid faculty-class data: ' + str(e))
    
    return render_template('step5_faculty_classes.html', 
                         faculties=faculties, 
                         class_names=class_names, 
                         subjects_per_class=subjects_per_class)

@app.route('/generate', methods=['GET', 'POST'])
def generate():
    """Generate the timetable"""
    class_names = session.get('class_names')
    subjects_per_class = session.get('subjects_per_class')
    faculties = session.get('faculties')
    faculty_classes = session.get('faculty_classes')
    periods = session.get('periods_per_day')
    limit = session.get('workload_limit', 28)

    if not all([class_names, subjects_per_class, faculties, periods]):
        return redirect(url_for('step1'))

    days = DAYS
    schedule = {c: {d: {p: None for p in range(1, periods + 1)} for d in days} for c in class_names}
    faculty_view = {f['name']: [] for f in faculties}
    load_summary = []
    warnings = []

    # Build a lookup for faculty by subject
    subject_faculty = {}
    for fac in faculties:
        for sub in fac['subjects']:
            subject_faculty.setdefault(sub, []).append(fac['name'])

    # Build a lookup for faculty assignments
    faculty_load = {f['name']: 0 for f in faculties}

    # Track faculty assignments per day/period to prevent clashes
    faculty_busy = {f['name']: {d: set() for d in days} for f in faculties}

    # Get edited cells from session
    edited_cells = session.get('edited_cells', {})

    # Define morning and afternoon periods
    morning_periods = [1, 2, 3, 4]
    afternoon_periods = [5, 6, 7] if periods >= 7 else [5, 6]

    for cname in class_names:
        subjects = subjects_per_class.get(cname, [])
        if not subjects:
            continue
        
        # Separate labs and theory
        labs = [s for s in subjects if s.get('type', 'theory') == 'lab']
        theory = [s for s in subjects if s.get('type', 'theory') != 'lab']
        
        # Track which slots are filled
        filled = {d: set() for d in days}
        
        # Place edited cells first
        for day in days:
            for period in range(1, periods + 1):
                cell_id = f"{cname}-{day}-{period}"
                if cell_id in edited_cells:
                    cell = edited_cells[cell_id]
                    schedule[cname][day][period] = {
                        'subject': cell['subject'],
                        'faculty': cell['faculty'],
                        'unassigned': False,
                        'overwork': False,
                        'edited': True
                    }
                    filled[day].add(period)
                    # Mark faculty as busy for this slot, only if valid
                    fac_name = cell.get('faculty', '')
                    if fac_name and fac_name != 'N/A' and fac_name in faculty_busy:
                        faculty_busy[fac_name][day].add(period)
                        faculty_view[fac_name].append({
                            'day': day,
                            'period': period,
                            'class': cname,
                            'subject': cell['subject'],
                            'overwork': False
                        })
                        faculty_load[fac_name] += 1

        # Assign labs in valid blocks
        for lab in labs:
            blocks_needed = lab.get('periods', 0) // lab.get('lab_block', 1)
            block_size = lab.get('lab_block', 1)
            subject_name = lab['name']
            fac_list = subject_faculty.get(subject_name, [])
            assigned_blocks = 0
            
            random_days = list(range(len(days)))
            random.shuffle(random_days)
            
            for day_idx in random_days:
                if assigned_blocks >= blocks_needed:
                    break
                
                day = days[day_idx]
                
                # Determine valid block starts for this block size
                valid_starts = []
                if block_size == 4:
                    valid_starts = [1]  # Only 1-4 in morning
                elif block_size == 3:
                    for start in range(1, periods - block_size + 2):
                        if start <= 4 and start + block_size - 1 >= 5:
                            continue
                        valid_starts.append(start)
                
                random.shuffle(valid_starts)
                
                for start in valid_starts:
                    block_range = list(range(start, start + block_size))
                    # Skip if any slot in block is already filled
                    if any(p in filled[day] for p in block_range):
                        continue
                    
                    # Check if block fits within morning or afternoon
                    if block_size == 3 and start == 5:
                        if max(block_range) > periods:
                            continue
                    elif max(block_range) > 4 and start < 5:
                        continue
                    
                    # Try to assign faculty for this block
                    slot_busy = {(day_idx, p): {f for f in faculty_busy if p in faculty_busy[f][day]} for p in block_range}
                    
                    for period in block_range:
                        fac_name, overwork = choose_faculty_for_slot(subject_name, day_idx, period, faculties, slot_busy, faculty_load, limit)
                        if not fac_name:
                            break
                    else:
                        # All periods in block can be assigned
                        for period in block_range:
                            fac_name, overwork = choose_faculty_for_slot(subject_name, day_idx, period, faculties, slot_busy, faculty_load, limit)
                            schedule[cname][day][period] = {
                                'subject': subject_name,
                                'faculty': fac_name,
                                'unassigned': False,
                                'overwork': overwork
                            }
                            filled[day].add(period)
                            faculty_busy[fac_name][day].add(period)
                            faculty_view[fac_name].append({
                                'day': day,
                                'period': period,
                                'class': cname,
                                'subject': subject_name,
                                'overwork': overwork
                            })
                            faculty_load[fac_name] += 1
                        
                        assigned_blocks += 1
                        break

        # Assign theory subjects to remaining slots
        for theory_sub in theory:
            subject_name = theory_sub['name']
            periods_needed = theory_sub.get('periods', 0)
            assigned_periods = 0
            
            # Create list of all available slots
            available_slots = []
            for day_idx, day in enumerate(days):
                for period in range(1, periods + 1):
                    if period not in filled[day]:
                        available_slots.append((day_idx, day, period))
            
            random.shuffle(available_slots)
            
            for day_idx, day, period in available_slots:
                if assigned_periods >= periods_needed:
                    break
                
                slot_busy = {(day_idx, period): {f for f in faculty_busy if period in faculty_busy[f][day]}}
                fac_name, overwork = choose_faculty_for_slot(subject_name, day_idx, period, faculties, slot_busy, faculty_load, limit)
                
                if fac_name:
                    schedule[cname][day][period] = {
                        'subject': subject_name,
                        'faculty': fac_name,
                        'unassigned': False,
                        'overwork': overwork
                    }
                    filled[day].add(period)
                    faculty_busy[fac_name][day].add(period)
                    faculty_view[fac_name].append({
                        'day': day,
                        'period': period,
                        'class': cname,
                        'subject': subject_name,
                        'overwork': overwork
                    })
                    faculty_load[fac_name] += 1
                    assigned_periods += 1
                else:
                    # Mark as unassigned
                    schedule[cname][day][period] = {
                        'subject': subject_name,
                        'faculty': 'N/A',
                        'unassigned': True,
                        'overwork': False
                    }
                    filled[day].add(period)
                    warnings.append(f"Could not assign faculty for {subject_name} in {cname} on {day} period {period}")

    # Generate load summary
    for fac_name, load in faculty_load.items():
        load_summary.append({
            'faculty': fac_name,
            'count': load,
            'over_limit': load > limit
        })

    # Create subject-faculty mapping for edit mode
    subject_faculty_map = {}
    for fac in faculties:
        for subject in fac['subjects']:
            if subject not in subject_faculty_map:
                subject_faculty_map[subject] = []
            subject_faculty_map[subject].append(fac['name'])

    return render_template('timetable.html',
                         class_names=class_names,
                         subjects_per_class=subjects_per_class,
                         faculties=faculties,
                         schedule=schedule,
                         faculty_view=faculty_view,
                         load_summary=load_summary,
                         warnings=warnings,
                         days=days,
                         periods=periods,
                         limit=limit,
                         subjectFacultyMap=json.dumps(subject_faculty_map))

@app.route('/edit_mode', methods=['POST'])
def edit_mode():
    """Toggle edit mode"""
    session['edit_mode'] = not session.get('edit_mode', False)
    return redirect(url_for('generate'))

@app.route('/save_edits', methods=['POST'])
def save_edits():
    """Save edits and rebalance timetable"""
    # Parse edited cells from form data
    edited_cells = {}
    for key, value in request.form.items():
        if key.startswith('subject-'):
            cell_id = key[len('subject-'):]
            subject = value
            faculty = request.form.get(f'faculty-{cell_id}', '')
            edited_cells[cell_id] = {'subject': subject, 'faculty': faculty}
    
    session['edited_cells'] = edited_cells
    session['edit_mode'] = False
    return redirect(url_for('generate'))

@app.route('/refresh/<class_name>')
def refresh_class(class_name):
    """Refresh timetable for a single class"""
    # For now, just redirect to full refresh
    return redirect(url_for('generate'))

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return render_template('error.html', msg="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return render_template('error.html', msg="Internal server error"), 500
