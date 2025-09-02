

from flask import Flask, render_template, request, redirect, url_for, session

import random, json



app = Flask(__name__)


# --- Edit Mode Backend Support ---
# Toggle edit mode
@app.route('/edit_mode', methods=['POST'])
def edit_mode():
    session['edit_mode'] = not session.get('edit_mode', False)
    return redirect(url_for('generate'))

# Save edits and rebalance timetable
@app.route('/save_edits', methods=['POST'])
def save_edits():
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

# Add refresh route for per-class timetable refresh
@app.route('/refresh/<class_name>')
def refresh_class(class_name):
    # Regenerate timetable for a single class and redirect to timetable
    # For now, just redirect to /generate (full refresh)
    return redirect(url_for('generate'))



@app.route('/')
def home():
    return render_template('step1.html')

@app.route('/add_class', methods=['GET', 'POST'])
def add_class():
    if request.method == 'POST':
        class_name = request.form['class_name']
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('INSERT INTO classes (name) VALUES (%s)', (class_name,))
            conn.commit()
            cursor.close()
            conn.close()
            return redirect(url_for('show_classes'))
        except Exception as e:
            return render_template('error.html', msg=f"DB Error: {e}")
    return render_template('add_Class.html')

@app.route('/show_classes')
def show_classes():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM classes')
        classes = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('show_classes.html', classes=classes)
    except Exception as e:
        return render_template('error.html', msg=f"DB Error: {e}")

DAYS = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday']

def choose_faculty_for_slot(subject, day_idx, period, faculties, slot_busy, load, limit):
    eligible = [f for f in faculties if subject in f['subjects']]
    if not eligible:
        return
    free_now = [f for f in eligible if f['name'] not in slot_busy.get((day_idx, period), set())]
    def pick_min_load(cands):
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

@app.route('/', methods=['GET', 'POST'])
def step1():
    if request.method == 'POST':
        session['num_classes'] = int(request.form['num_classes'])
        session['periods_per_day'] = int(request.form['periods_per_day'])
        session['workload_limit'] = int(request.form['workload_limit'])
        return redirect(url_for('step2_classes'))
    return render_template('step1.html')

@app.route('/classes', methods=['GET','POST'])
def step2_classes():
    num = session.get('num_classes')
    if not num:
        return redirect(url_for('step1'))
    if request.method == 'POST':
        class_names = [request.form[f'class_name_{i}'] for i in range(1, num+1)]
        session['class_names'] = class_names
        return redirect(url_for('step3_subjects'))
    return render_template('step2_classes.html', num=num)

@app.route('/subjects', methods=['GET', 'POST'])
def step3_subjects():
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
        except Exception as e:
            return render_template('error.html', msg=f'Invalid subjects data: {e}')
        return redirect(url_for('step4_faculties'))
    return render_template('step3_subjects.html', class_names=class_names)

@app.route('/faculties', methods=['GET', 'POST'])
def step4_faculties():
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
        except Exception as e:
            return render_template('error.html', msg='Invalid faculties data: ' + str(e))
        return redirect(url_for('step5_faculty_classes'))
    return render_template('step4_faculties.html', unique_subjects=unique_subjects)

@app.route('/faculty_classes', methods=['GET', 'POST'])
def step5_faculty_classes():
    faculties = session.get('faculties')
    class_names = session.get('class_names')
    subjects_per_class = session.get('subjects_per_class', {})
    if not faculties or not class_names:
        return redirect(url_for('step1'))
    if request.method == 'POST':
        faculty_classes_json = request.form.get('faculty_classes_json', 'null')
        try:
            faculty_classes = json.loads(faculty_classes_json)
        except Exception as e:
            return render_template('error.html', msg='Invalid faculty-class data: ' + str(e))
        session['faculty_classes'] = faculty_classes
        return redirect(url_for('generate'))
    return render_template('step5_faculty_classes.html', faculties=faculties, class_names=class_names, subjects_per_class=subjects_per_class)

@app.route('/generate', methods=['GET', 'POST'])
def generate():
    class_names = session.get('class_names')
    subjects_per_class = session.get('subjects_per_class')
    faculties = session.get('faculties')
    faculty_classes = session.get('faculty_classes')
    periods = session.get('periods_per_day')
    limit = session.get('workload_limit', 28)

    if not all([class_names, subjects_per_class, faculties, faculty_classes, periods]):
        return redirect(url_for('step1'))

    import random
    days = DAYS
    schedule = {c: {d: {p: None for p in range(1, periods+1)} for d in days} for c in class_names}
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

    # For each class, assign labs in blocks, then fill with theory
    # Track faculty assignments per day/period to prevent clashes
    faculty_busy = {f['name']: {d: set() for d in days} for f in faculties}

    # Get edited cells from session
    edited_cells = session.get('edited_cells', {})

    # Define morning and afternoon periods
    morning_periods = [1, 2, 3, 4]
    afternoon_periods = [5, 6, 7]

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
            for period in range(1, periods+1):
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
        # Assign labs in valid blocks, randomizing lab days
        for lab in labs:
            blocks_needed = lab.get('periods', 0) // lab.get('lab_block', 1)
            block_size = lab.get('lab_block', 1)
            subject_name = lab['name']
            fac_list = subject_faculty.get(subject_name, [])
            assigned_blocks = 0
            random_days = days[:]
            random.shuffle(random_days)
            for day in random_days:
                if assigned_blocks >= blocks_needed:
                    break
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
                    # Skip if any slot in block is already filled (by edit or previous assignment)
                    if any(p in filled[day] for p in block_range):
                        continue
                    if block_size == 3 and start == 5:
                        if max(block_range) > 7:
                            continue
                    elif max(block_range) > 4 and start < 5:
                        continue
                    for fac_name in fac_list:
                        if all(p not in faculty_busy[fac_name][day] for p in block_range):
                            for p in block_range:
                                schedule[cname][day][p] = {
                                    'subject': subject_name,
                                    'faculty': fac_name,
                                    'unassigned': False,
                                    'overwork': False
                                }
                                filled[day].add(p)
                                faculty_busy[fac_name][day].add(p)
                                faculty_view[fac_name].append({
                                    'day': day,
                                    'period': p,
                                    'class': cname,
                                    'subject': subject_name,
                                    'overwork': False
                                })
                                faculty_load[fac_name] += 1
                            assigned_blocks += 1
                            break
                    if assigned_blocks >= blocks_needed:
                        break
                if assigned_blocks >= blocks_needed:
                    break
        # Assign theory subjects to remaining slots
        expanded_theory = []
        for subj in theory:
            for _ in range(subj.get('periods', 1)):
                expanded_theory.append(subj)
        random.shuffle(expanded_theory)
        idx = 0
        for day in days:
            for period in range(1, periods+1):
                if period in filled[day]:
                    continue
                if idx >= len(expanded_theory):
                    continue
                subj = expanded_theory[idx]
                subject_name = subj['name']
                fac_list = subject_faculty.get(subject_name, [])
                fac_name = 'N/A'
                free_facs = [f for f in fac_list if period not in faculty_busy[f][day]]
                if free_facs:
                    fac_name = random.choice(free_facs)
                schedule[cname][day][period] = {
                    'subject': subject_name,
                    'faculty': fac_name,
                    'unassigned': fac_name == 'N/A',
                    'overwork': False
                }
                if fac_name != 'N/A':
                    faculty_view[fac_name].append({
                        'day': day,
                        'period': period,
                        'class': cname,
                        'subject': subject_name,
                        'overwork': False
                    })
                    faculty_load[fac_name] += 1
                    faculty_busy[fac_name][day].add(period)
                idx += 1

    # Build load summary
    for fac in faculties:
        name = fac['name']
        count = faculty_load.get(name, 0)
        over_limit = count > limit
        load_summary.append({'faculty': name, 'count': count, 'over_limit': over_limit})

    # Build subjectFacultyMap for frontend
    subjectFacultyMap = {}
    for fac in faculties:
        for subj in fac['subjects']:
            subjectFacultyMap.setdefault(subj, []).append(fac['name'])

    import json as pyjson
    return render_template('timetable.html',
        class_names=class_names,
        periods=periods,
        days=days,
        schedule=schedule,
        faculty_view=faculty_view,
        load_summary=load_summary,
        warnings=warnings,
        limit=limit,
        subjects_per_class=subjects_per_class,
        subjectFacultyMap=pyjson.dumps(subjectFacultyMap)
    )


if __name__ == '__main__':
    app.run(debug=True)
