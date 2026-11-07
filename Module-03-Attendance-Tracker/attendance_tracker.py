"""
ATTENDANCE TRACKER - Python Mini Project
Run: python attendance_tracker.py

Features:
- Student and subject management
- Date-wise, subject-wise attendance marking
- Attendance percentage and status analysis
- Recovery and safe-absence calculators
- Student, subject, monthly and class reports
- CSV export and JSON file persistence

Concepts: lists, dictionaries, sets, tuples, comprehensions, strings,
nested data, datetime, functions, validation and exception handling.
"""
import csv
import json
import math
from datetime import date, datetime, timedelta
from pathlib import Path

DATA_FILE = Path(__file__).with_name("attendance_data.json")
CSV_FILE = Path(__file__).with_name("attendance_report.csv")
STATUS_BANDS = ((85, "EXCELLENT"), (75, "SAFE"), (65, "AT RISK"), (0, "CRITICAL"))


def empty_data():
    return {"students": [], "subjects": [], "records": [], "settings": {"threshold": 75.0}}


def load_data():
    if not DATA_FILE.exists():
        return empty_data()
    try:
        with DATA_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        for key in ("students", "subjects", "records"):
            if not isinstance(data.get(key), list):
                data[key] = []
        data.setdefault("settings", {"threshold": 75.0})
        data["settings"].setdefault("threshold", 75.0)
        return data
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Could not load saved data: {exc}")
        return empty_data()


def save_data(data):
    try:
        with DATA_FILE.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except OSError as exc:
        print(f"Could not save data: {exc}")


def make_id(items, prefix):
    used = {item["id"] for item in items}
    number = 1
    while f"{prefix}{number:03d}" in used:
        number += 1
    return f"{prefix}{number:03d}"


def heading(title):
    print("\n" + "=" * 68)
    print(title.center(68))
    print("=" * 68)


def pause():
    input("\nPress Enter to continue...")


def ask_text(prompt):
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("This field cannot be empty.")


def ask_date():
    while True:
        value = input("Date (YYYY-MM-DD): ").strip()
        try:
            parsed = datetime.strptime(value, "%Y-%m-%d").date()
            if parsed > date.today():
                print("Future attendance dates are not allowed.")
                continue
            return parsed.isoformat()
        except ValueError:
            print("Invalid date. Example: 2026-11-07")


def ask_number(prompt, low=1, high=100):
    while True:
        try:
            value = float(input(prompt))
            if low <= value <= high:
                return value
            print(f"Enter a value from {low} to {high}.")
        except ValueError:
            print("Enter a valid number.")


def yes_no(prompt):
    return input(prompt + " (y/n): ").strip().lower() in ("y", "yes")


def student_by_id(data, sid):
    return next((s for s in data["students"] if s["id"].lower() == sid.lower()), None)


def subject_by_id(data, subid):
    return next((s for s in data["subjects"] if s["id"].lower() == subid.lower()), None)


def student_records(data, sid, subid=None):
    return [r for r in data["records"]
            if r["student_id"] == sid and (subid is None or r["subject_id"] == subid)]


def stats(records):
    total = len(records)
    present = sum(r["status"] == "Present" for r in records)
    absent = total - present
    return {"total": total, "present": present, "absent": absent,
            "percentage": present * 100 / total if total else 0.0}


def student_stats(data, sid):
    return stats(student_records(data, sid))


def subject_stats(data, subid):
    return stats([r for r in data["records"] if r["subject_id"] == subid])


def classify(percent):
    if percent >= 85:
        return "EXCELLENT"
    if percent >= 75:
        return "SAFE"
    if percent >= 65:
        return "AT RISK"
    return "CRITICAL"


def threshold(data):
    try:
        value = float(data["settings"].get("threshold", 75))
        return value if 1 <= value <= 100 else 75.0
    except (ValueError, TypeError):
        return 75.0


def recovery_classes(attended, total, target):
    """Minimum consecutive presents needed: (A+x)/(T+x) >= target."""
    if total == 0 or attended / total >= target / 100:
        return 0
    if target == 100:
        return total - attended
    return max(0, math.ceil((target * total / 100 - attended) / (1 - target / 100)))


def safe_absences(attended, total, target):
    """Maximum consecutive absences while retaining the target percentage."""
    if total == 0 or attended / total < target / 100:
        return 0
    if target == 0:
        return 999999
    return max(0, math.floor(attended / (target / 100)) - total)


# -------------------------- Students ---------------------------------

def add_student(data):
    heading("ADD STUDENT")
    sid = ask_text("Student ID: ").upper()
    if student_by_id(data, sid):
        print("That student ID already exists.")
        return
    roll = ask_text("Roll number: ")
    if any(s["roll"].lower() == roll.lower() for s in data["students"]):
        print("That roll number is already in use.")
        return
    data["students"].append({
        "id": sid, "name": ask_text("Name: "),
        "roll": roll, "section": ask_text("Section: ").upper()
    })
    save_data(data)
    print("Student added successfully.")


def update_student(data):
    heading("UPDATE STUDENT")
    sid = input("Student ID: ").strip().upper()
    student = student_by_id(data, sid)
    if not student:
        print("Student not found.")
        return
    print("Press Enter to retain the current value.")
    name = input(f"Name [{student['name']}]: ").strip()
    roll = input(f"Roll [{student['roll']}]: ").strip()
    section = input(f"Section [{student['section']}]: ").strip().upper()
    if name:
        student["name"] = name
    if roll and not any(s["roll"].lower() == roll.lower() and s["id"] != sid
                        for s in data["students"]):
        student["roll"] = roll
    elif roll:
        print("Roll number belongs to another student; unchanged.")
    if section:
        student["section"] = section
    save_data(data)
    print("Student updated.")


def delete_student(data):
    heading("DELETE STUDENT")
    sid = input("Student ID: ").strip().upper()
    student = student_by_id(data, sid)
    if not student:
        print("Student not found.")
        return
    if yes_no(f"Delete {student['name']} and their attendance records?"):
        data["students"] = [s for s in data["students"] if s["id"] != sid]
        data["records"] = [r for r in data["records"] if r["student_id"] != sid]
        save_data(data)
        print("Student and related records deleted.")


def list_students(data):
    heading("STUDENT LIST")
    if not data["students"]:
        print("No students available.")
        return
    print(f"{'ID':<10}{'NAME':<25}{'ROLL':<10}{'SECTION':<12}{'ATTENDANCE':>11}")
    print("-" * 68)
    for s in sorted(data["students"], key=lambda x: x["name"].lower()):
        result = student_stats(data, s["id"])
        pct = f"{result['percentage']:.1f}%" if result["total"] else "N/A"
        print(f"{s['id']:<10}{s['name'][:23]:<25}{s['roll']:<10}{s['section']:<12}{pct:>11}")


def search_student(data):
    heading("SEARCH STUDENT")
    q = ask_text("Search name, ID, roll or section: ").lower()
    matches = [s for s in data["students"]
               if q in s["name"].lower() or q in s["id"].lower()
               or q in s["roll"].lower() or q in s["section"].lower()]
    if not matches:
        print("No matching student.")
    for s in matches:
        result = student_stats(data, s["id"])
        print(f"{s['id']} | {s['name']} | {s['section']} | {result['percentage']:.1f}%")


def student_menu(data):
    while True:
        heading("STUDENT MANAGEMENT")
        print("1 Add  2 Update  3 Delete  4 List  5 Search  0 Back")
        choice = input("Choice: ").strip()
        if choice == "1":
            add_student(data)
        elif choice == "2":
            update_student(data)
        elif choice == "3":
            delete_student(data)
        elif choice == "4":
            list_students(data)
        elif choice == "5":
            search_student(data)
        elif choice == "0":
            return
        else:
            print("Invalid menu choice.")
        pause()


# -------------------------- Subjects ---------------------------------

def add_subject(data):
    heading("ADD SUBJECT")
    subid = ask_text("Subject ID: ").upper()
    if subject_by_id(data, subid):
        print("Subject ID already exists.")
        return
    data["subjects"].append({
        "id": subid, "name": ask_text("Subject name: "),
        "faculty": ask_text("Faculty name: ")
    })
    save_data(data)
    print("Subject added.")


def list_subjects(data):
    heading("SUBJECT LIST")
    if not data["subjects"]:
        print("No subjects available.")
        return
    for sub in data["subjects"]:
        result = subject_stats(data, sub["id"])
        print(f"{sub['id']:<10} {sub['name']:<30} Faculty: {sub['faculty']}"
              f" | Attendance: {result['percentage']:.1f}%")


def update_subject(data):
    subid = input("Subject ID: ").strip().upper()
    sub = subject_by_id(data, subid)
    if not sub:
        print("Subject not found.")
        return
    name = input(f"Name [{sub['name']}]: ").strip()
    faculty = input(f"Faculty [{sub['faculty']}]: ").strip()
    if name:
        sub["name"] = name
    if faculty:
        sub["faculty"] = faculty
    save_data(data)
    print("Subject updated.")


def delete_subject(data):
    subid = input("Subject ID: ").strip().upper()
    sub = subject_by_id(data, subid)
    if not sub:
        print("Subject not found.")
        return
    if yes_no(f"Delete {sub['name']} and its attendance records?"):
        data["subjects"] = [s for s in data["subjects"] if s["id"] != subid]
        data["records"] = [r for r in data["records"] if r["subject_id"] != subid]
        save_data(data)
        print("Subject and related records deleted.")


def subject_menu(data):
    while True:
        heading("SUBJECT MANAGEMENT")
        print("1 Add  2 Update  3 Delete  4 List  0 Back")
        choice = input("Choice: ").strip()
        if choice == "1":
            add_subject(data)
        elif choice == "2":
            update_subject(data)
        elif choice == "3":
            delete_subject(data)
        elif choice == "4":
            list_subjects(data)
        elif choice == "0":
            return
        else:
            print("Invalid menu choice.")
        pause()


# -------------------------- Attendance --------------------------------

def mark_attendance(data):
    heading("MARK ATTENDANCE")
    if not data["students"] or not data["subjects"]:
        print("Add students and subjects first.")
        return
    list_subjects(data)
    subid = input("Subject ID: ").strip().upper()
    subject = subject_by_id(data, subid)
    if not subject:
        print("Invalid subject.")
        return
    day = ask_date()
    if any(r["subject_id"] == subid and r["date"] == day for r in data["records"]):
        print("Attendance already exists for this subject and date.")
        return

    section = input("Section filter (Enter for all): ").strip().upper()
    students = [s for s in data["students"] if not section or s["section"] == section]
    if not students:
        print("No students found for that section.")
        return

    new_records = []
    for index, student in enumerate(sorted(students, key=lambda x: x["roll"])):
        while True:
            answer = input(f"{student['roll']} - {student['name']} [P/A/M=remaining present]: ").strip().upper()
            if answer in ("P", "PRESENT"):
                status = "Present"
                break
            if answer in ("A", "ABSENT"):
                status = "Absent"
                break
            if answer == "M":
                for remaining in sorted(students, key=lambda x: x["roll"])[index:]:
                    new_records.append({
                        "id": make_id(data["records"] + new_records, "A"),
                        "student_id": remaining["id"], "subject_id": subid,
                        "date": day, "status": "Present"
                    })
                break
            print("Invalid status. Enter P, A or M.")
        if answer == "M":
            break
        new_records.append({
            "id": make_id(data["records"] + new_records, "A"),
            "student_id": student["id"], "subject_id": subid,
            "date": day, "status": status
        })

    data["records"].extend(new_records)
    save_data(data)
    present = sum(r["status"] == "Present" for r in new_records)
    print(f"Saved {len(new_records)} records: {present} Present, {len(new_records)-present} Absent.")


def daily_attendance(data):
    day = ask_date()
    subid = input("Subject ID (Enter for all): ").strip().upper()
    records = [r for r in data["records"] if r["date"] == day
               and (not subid or r["subject_id"] == subid)]
    if not records:
        print("No records found.")
        return
    for r in records:
        student = student_by_id(data, r["student_id"])
        subject = subject_by_id(data, r["subject_id"])
        print(f"{student['name'] if student else r['student_id']:<24} "
              f"{subject['name'] if subject else r['subject_id']:<28} {r['status']}")


def history(data):
    sid = input("Student ID: ").strip().upper()
    student = student_by_id(data, sid)
    if not student:
        print("Student not found.")
        return
    subid = input("Subject ID (Enter for all): ").strip().upper()
    records = sorted(student_records(data, sid, subid or None),
                     key=lambda r: r["date"], reverse=True)
    if not records:
        print("No attendance history.")
    for r in records:
        subject = subject_by_id(data, r["subject_id"])
        print(f"{r['date']} | {subject['name'] if subject else r['subject_id']} | {r['status']}")


def attendance_menu(data):
    while True:
        heading("ATTENDANCE MANAGEMENT")
        print("1 Mark attendance  2 Daily attendance  3 Student history  0 Back")
        choice = input("Choice: ").strip()
        if choice == "1":
            mark_attendance(data)
        elif choice == "2":
            daily_attendance(data)
        elif choice == "3":
            history(data)
        elif choice == "0":
            return
        else:
            print("Invalid menu choice.")
        pause()


# -------------------------- Reports / analytics -----------------------

def student_report(data):
    sid = input("Student ID: ").strip().upper()
    student = student_by_id(data, sid)
    if not student:
        print("Student not found.")
        return
    records = student_records(data, sid)
    result = stats(records)
    limit = threshold(data)
    print(f"\nREPORT: {student['name']} ({sid})")
    print(f"Section: {student['section']} | Roll: {student['roll']}")
    print(f"Present: {result['present']} | Absent: {result['absent']} | Total: {result['total']}")
    print(f"Attendance: {result['percentage']:.2f}% | Status: {classify(result['percentage'])}")
    for sub in data["subjects"]:
        sr = stats(student_records(data, sid, sub["id"]))
        if sr["total"]:
            print(f"{sub['name']}: {sr['percentage']:.2f}% ({sr['present']}/{sr['total']})")
    if result["total"]:
        print(f"Classes to attend to reach {limit:.1f}%: "
              f"{recovery_classes(result['present'], result['total'], limit)}")
        print(f"Safe future absences at {limit:.1f}%: "
              f"{safe_absences(result['present'], result['total'], limit)}")


def class_summary(data):
    records = data["records"]
    result = stats(records)
    print(f"Students: {len(data['students'])} | Subjects: {len(data['subjects'])}")
    print(f"Attendance entries: {result['total']} | Present: {result['present']} | Absent: {result['absent']}")
    print(f"Overall attendance: {result['percentage']:.2f}%")
    # Dictionary comprehension: count students in each attendance category.
    distribution = {
        band: sum(
            classify(student_stats(data, s["id"])["percentage"]) == band
            for s in data["students"] if student_stats(data, s["id"])["total"]
        )
        for band in ("EXCELLENT", "SAFE", "AT RISK", "CRITICAL")
    }
    print("Status distribution:", distribution)


def subject_report(data):
    for sub in data["subjects"]:
        result = subject_stats(data, sub["id"])
        print(f"{sub['name']:<30} {result['percentage']:>6.2f}% "
              f"({result['present']}/{result['total']})")


def alerts(data):
    flagged = []
    for s in data["students"]:
        result = student_stats(data, s["id"])
        if result["total"] and classify(result["percentage"]) in ("AT RISK", "CRITICAL"):
            flagged.append((s, result))
    flagged.sort(key=lambda item: item[1]["percentage"])
    if not flagged:
        print("No at-risk or critical students.")
    for s, result in flagged:
        print(f"{classify(result['percentage']):<10} {s['id']} {s['name']:<22} "
              f"{result['percentage']:.2f}%")


def monthly_summary(data):
    month = input("Month (YYYY-MM; Enter for current month): ").strip()
    if not month:
        month = date.today().strftime("%Y-%m")
    try:
        datetime.strptime(month, "%Y-%m")
    except ValueError:
        print("Invalid month. Use YYYY-MM.")
        return
    result = stats([r for r in data["records"] if r["date"].startswith(month)])
    print(f"{month}: {result['total']} entries | Present {result['present']} | "
          f"Absent {result['absent']} | {result['percentage']:.2f}%")


def reports_menu(data):
    while True:
        heading("ANALYTICS & REPORTS")
        print("1 Class summary  2 Subject report  3 Student report")
        print("4 Defaulter list  5 Monthly summary  0 Back")
        choice = input("Choice: ").strip()
        if choice == "1":
            class_summary(data)
        elif choice == "2":
            subject_report(data)
        elif choice == "3":
            student_report(data)
        elif choice == "4":
            alerts(data)
        elif choice == "5":
            monthly_summary(data)
        elif choice == "0":
            return
        else:
            print("Invalid menu choice.")
        pause()


# -------------------------- Calculators / settings ---------------------

def calculator(data):
    sid = input("Student ID: ").strip().upper()
    student = student_by_id(data, sid)
    if not student:
        print("Student not found.")
        return
    subid = input("Subject ID (Enter for overall): ").strip().upper()
    if subid and not subject_by_id(data, subid):
        print("Invalid subject.")
        return
    result = stats(student_records(data, sid, subid or None))
    if not result["total"]:
        print("No attendance records available.")
        return
    target = ask_number("Target percentage (1-100): ")
    print(f"Current attendance: {result['percentage']:.2f}%")
    print(f"Consecutive classes to attend: "
          f"{recovery_classes(result['present'], result['total'], target)}")
    print(f"Future absences possible: "
          f"{safe_absences(result['present'], result['total'], target)}")


def change_threshold(data):
    print(f"Current threshold: {threshold(data):.1f}%")
    data["settings"]["threshold"] = ask_number("New threshold (1-100): ")
    save_data(data)
    print("Threshold updated.")


# -------------------------- CSV export ---------------------------------

def export_csv(data):
    try:
        with CSV_FILE.open("w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file)
            writer.writerow(["Record ID", "Student ID", "Student Name", "Roll",
                             "Section", "Subject", "Date", "Status"])
            for r in data["records"]:
                s = student_by_id(data, r["student_id"])
                sub = subject_by_id(data, r["subject_id"])
                writer.writerow([
                    r["id"], r["student_id"], s["name"] if s else "",
                    s["roll"] if s else "", s["section"] if s else "",
                    sub["name"] if sub else "", r["date"], r["status"]
                ])
        print(f"CSV exported to: {CSV_FILE}")
    except OSError as exc:
        print(f"CSV export failed: {exc}")


# -------------------------- Demo data ----------------------------------

def load_demo_data(data):
    if (data["students"] or data["subjects"] or data["records"]) and not yes_no(
        "Replace existing data with demo data?"
    ):
        print("Cancelled.")
        return

    names = [
        "Aarav Sharma", "Ananya Rao", "Arjun Nair", "Diya Menon",
        "Ishaan Gupta", "Meera Thomas", "Rohan Kumar", "Aditi Shah",
        "Karthik Reddy", "Sneha Iyer", "Rahul Das", "Nisha Verma",
        "Aditya Raj", "Pooja Nair", "Varun Patel", "Kavya Menon",
        "Dev Malhotra", "Sana Khan", "Vivek S", "Maya Joseph"
    ]
    rates = [0.98, .95, .92, .90, .88, .86, .84, .82, .80, .78,
             .76, .74, .72, .70, .68, .65, .62, .58, .55, .50]
    students = [
        {"id": f"S{i:03d}", "name": name, "roll": f"{i:02d}",
         "section": "CSE-A" if i <= 10 else "CSE-B"}
        for i, name in enumerate(names, 1)
    ]
    subjects = [
        {"id": "SUB01", "name": "Data Structures", "faculty": "Dr. Sharma"},
        {"id": "SUB02", "name": "Operating Systems", "faculty": "Prof. Menon"},
        {"id": "SUB03", "name": "Computer Networks", "faculty": "Dr. Rao"},
        {"id": "SUB04", "name": "Database Management", "faculty": "Prof. Thomas"},
        {"id": "SUB05", "name": "Web Technologies", "faculty": "Ms. Iyer"}
    ]

    weekdays = []
    current = date.today() - timedelta(days=27)
    while current <= date.today():
        if current.weekday() < 5:
            weekdays.append(current)
        current += timedelta(days=1)
    weekdays = weekdays[-12:]

    records = []
    counter = 1
    for sj, subject in enumerate(subjects):
        for di, class_day in enumerate(weekdays):
            for si, student in enumerate(students):
                adjusted_rate = max(0, rates[si] - ((si + sj + di) % 5) * .015)
                present = ((si * 7 + sj * 3 + di * 5) % 100) < int(adjusted_rate * 100)
                records.append({
                    "id": f"A{counter:04d}", "student_id": student["id"],
                    "subject_id": subject["id"], "date": class_day.isoformat(),
                    "status": "Present" if present else "Absent"
                })
                counter += 1

    data["students"], data["subjects"], data["records"] = students, subjects, records
    data["settings"] = {"threshold": 75.0}
    save_data(data)
    print(f"Demo data loaded: {len(students)} students, {len(subjects)} subjects, "
          f"{len(records)} attendance records.")


def reset_data(data):
    if yes_no("Permanently clear all students, subjects and attendance records?"):
        data.clear()
        data.update(empty_data())
        save_data(data)
        print("All data cleared.")


# -------------------------- Dashboard / main ---------------------------

def dashboard(data):
    heading("ATTENDANCE TRACKER DASHBOARD")
    result = stats(data["records"])
    today_records = [r for r in data["records"] if r["date"] == date.today().isoformat()]
    today_result = stats(today_records)
    risk_count = sum(
        1 for s in data["students"]
        if student_stats(data, s["id"])["total"]
        and classify(student_stats(data, s["id"])["percentage"]) in ("AT RISK", "CRITICAL")
    )
    print(f"Date: {date.today().strftime('%d %B %Y')}")
    print(f"Students: {len(data['students'])} | Subjects: {len(data['subjects'])}")
    print(f"Overall attendance: {result['percentage']:.2f}%")
    print(f"Present entries: {result['present']} | Absent entries: {result['absent']}")
    print(f"Today's present: {today_result['present']} | Today's absent: {today_result['absent']}")
    print(f"Students at risk/critical: {risk_count}")
    print(f"Required threshold: {threshold(data):.1f}%")
    print("\nSubject performance:")
    for sub in data["subjects"]:
        sr = subject_stats(data, sub["id"])
        print(f"- {sub['name']}: {sr['percentage']:.2f}%")


def main():
    data = load_data()
    heading("WELCOME TO ATTENDANCE TRACKER")
    print("Student Attendance Management & Analytics System")
    if not data["students"] and not data["subjects"]:
        print("\nNo saved data found.")
        if yes_no("Load sample demonstration data now?"):
            load_demo_data(data)

    while True:
        heading("MAIN MENU")
        print("1 Dashboard")
        print("2 Student Management")
        print("3 Subject Management")
        print("4 Attendance Management")
        print("5 Analytics & Reports")
        print("6 Recovery / Safe-Absence Calculator")
        print("7 Change Attendance Threshold")
        print("8 Export CSV Report")
        print("9 Load Demo Data")
        print("10 Reset All Data")
        print("0 Exit")
        choice = input("\nSelect an option: ").strip()

        try:
            if choice == "1":
                dashboard(data)
                pause()
            elif choice == "2":
                student_menu(data)
            elif choice == "3":
                subject_menu(data)
            elif choice == "4":
                attendance_menu(data)
            elif choice == "5":
                reports_menu(data)
            elif choice == "6":
                calculator(data)
                pause()
            elif choice == "7":
                change_threshold(data)
                pause()
            elif choice == "8":
                export_csv(data)
                pause()
            elif choice == "9":
                load_demo_data(data)
                pause()
            elif choice == "10":
                reset_data(data)
                pause()
            elif choice == "0":
                save_data(data)
                print("Thank you for using Attendance Tracker.")
                break
            else:
                print("Invalid menu choice. Select 0-10.")
                pause()
        except (KeyError, TypeError) as exc:
            print(f"Data error: {exc}. Check the saved JSON data.")
            pause()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nApplication stopped. Previously saved data remains available.")
