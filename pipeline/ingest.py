import os
import requests
from datetime import datetime


def _infer_semester(date_str):
    if not date_str:
        return None
    try:
        clean = (
            date_str.replace(" +0000 UTC", "")
                    .replace("T", " ")
                    .split(".")[0]
                    .strip()
        )
        dt = datetime.strptime(clean, "%Y-%m-%d %H:%M:%S")
        suffix = str(dt.year)[2:]
        return f"FA{suffix}" if dt.month > 5 else f"SP{suffix}"
    except Exception:
        return None

CURRENT_SEMESTER = "FA26"
SEMESTERS = ["FA26", "SP26", "FA25", "SP25"]

RMP_URL = "https://www.ratemyprofessors.com/graphql"
RMP_HEADERS = {
    "Authorization": "Basic dGVzdDp0ZXN0",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://www.ratemyprofessors.com/"
}
RMP_SCHOOL_ID = "U2Nob29sLTI5OA=="
def _rmp_query(cursor=None):
    after = f', after: "{cursor}"' if cursor else ""
    return """
{
  newSearch {
    teachers(query: { text: "", schoolID: "%s", fallback: true }, first: 500%s) {
      pageInfo { hasNextPage endCursor }
      edges {
        node {
          firstName
          lastName
          department
          avgRating
          avgDifficulty
          numRatings
          ratings(first: 50) {
            edges {
              node {
                comment
                clarityRating
                difficultyRating
                helpfulRating
                date
                class
              }
            }
          }
        }
      }
    }
  }
}
""" % (RMP_SCHOOL_ID, after)


def fetch_cornell_courses(subject="CS", semesters=None):
    if semesters is None:
        semesters = SEMESTERS

    docs = []
    for semester in semesters:
        url = (
            f"https://classes.cornell.edu/api/2.0/search/classes.json"
            f"?roster={semester}&subject={subject}"
        )
        response = requests.get(url)
        if response.status_code != 200:
            continue
        data = response.json()
        if data.get("status") != "success":
            continue

        for course in data["data"]["classes"]:
            course_number = f"{course['subject']} {course['catalogNbr']}"
            title = course.get("titleLong", "")
            description = course.get("description", "")
            prereqs = course.get("catalogPrereqCoreq", "")

            instructors = []
            for group in course.get("enrollGroups", []):
                for section in group.get("classSections", []):
                    for meeting in section.get("meetings", []):
                        for instructor in meeting.get("instructors", []):
                            name = f"{instructor['firstName']} {instructor['lastName']}"
                            if name not in instructors:
                                instructors.append(name)

            text_parts = [f"{course_number}: {title}"]
            if description:
                text_parts.append(description)
            if prereqs:
                text_parts.append(f"Prerequisites: {prereqs}")

            docs.append({
                "text": " ".join(text_parts),
                "metadata": {
                    "source": "cornell_classes_api",
                    "doc_type": "course",
                    "course_number": course_number,
                    "semester": semester,
                    "instructors": ", ".join(instructors),
                    "is_current": semester == CURRENT_SEMESTER
                }
            })
    return docs


def fetch_rmp_professors():
    docs = []
    cursor = None

    while True:
        response = requests.post(
            RMP_URL,
            json={"query": _rmp_query(cursor)},
            headers=RMP_HEADERS
        )
        if response.status_code != 200:
            break

        teachers = (
            response.json()
            .get("data", {})
            .get("newSearch", {})
            .get("teachers", {})
        )
        edges = teachers.get("edges", [])
        page_info = teachers.get("pageInfo", {})

        for edge in edges:
            node = edge["node"]
            if node.get("department") != "Computer Science":
                continue

            professor_name = f"{node['firstName']} {node['lastName']}"
            avg_rating = node.get("avgRating")
            avg_difficulty = node.get("avgDifficulty")

            for rating_edge in node.get("ratings", {}).get("edges", []):
                rating = rating_edge["node"]
                comment = rating.get("comment", "").strip()
                if not comment:
                    continue
                course_class = rating.get("class", "")
                docs.append({
                    "text": f"Review of Professor {professor_name} for {course_class}: {comment}",
                    "metadata": {
                        "source": "ratemyprofessors",
                        "doc_type": "review",
                        "professor_name": professor_name,
                        "department": node.get("department"),
                        "class": course_class,
                        "clarity_rating": rating.get("clarityRating"),
                        "difficulty_rating": rating.get("difficultyRating"),
                        "helpful_rating": rating.get("helpfulRating"),
                        "date": rating.get("date", ""),
                        "avg_rating": avg_rating,
                        "avg_difficulty": avg_difficulty
                    }
                })

        if not page_info.get("hasNextPage"):
            break
        cursor = page_info.get("endCursor")

    return docs


def scrape_cureviews(course_numbers):
    docs = []
    for number in course_numbers:
        info_response = requests.post(
            "https://www.cureviews.org/api/courses/get-by-info",
            json={"subject": "CS", "number": number}
        )
        if info_response.status_code != 200:
            continue
        course = info_response.json().get("result")
        if not course:
            continue

        course_id = course["_id"]
        title = course.get("classTitle", "")
        sems = course.get("classSems", [])

        reviews_response = requests.post(
            "https://www.cureviews.org/api/courses/get-reviews",
            json={"courseId": course_id}
        )
        if reviews_response.status_code != 200:
            continue

        reviews = reviews_response.json().get("result", [])

        # Build professor-semester map from review dates
        sem_to_profs = {}
        for review in reviews:
            sem = _infer_semester(review.get("date", ""))
            if sem:
                profs = review.get("professors", [])
                sem_to_profs.setdefault(sem, set()).update(profs)

        fall_sems = sorted(s for s in sems if s.startswith("FA"))
        spring_sems = sorted(s for s in sems if s.startswith("SP"))

        prof_lines = [
            f"{sem}: {', '.join(sorted(profs))}"
            for sem, profs in sorted(sem_to_profs.items())
            if profs
        ]

        schedule_text = (
            f"CS {number} ({title}) semester history. "
            f"Fall semesters offered: {', '.join(fall_sems) or 'none recorded'}. "
            f"Spring semesters offered: {', '.join(spring_sems) or 'none recorded'}."
        )
        if prof_lines:
            schedule_text += (
                f" Professors by semester (inferred from student reviews): "
                + ". ".join(prof_lines) + "."
            )

        docs.append({
            "text": schedule_text,
            "metadata": {
                "source": "cureviews",
                "doc_type": "course_schedule",
                "course_number": f"CS {number}"
            }
        })

        for review in reviews:
            text = review.get("text", "").strip()
            if not text:
                continue
            docs.append({
                "text": f"CS {number} ({title}) review: {text}",
                "metadata": {
                    "source": "cureviews",
                    "doc_type": "review",
                    "course_number": f"CS {number}",
                    "professor": ", ".join(review.get("professors", [])),
                    "rating": review.get("rating"),
                    "difficulty": review.get("difficulty"),
                    "workload": review.get("workload"),
                    "date": review.get("date", "")
                }
            })
    return docs


def load_local_docs(directory):
    docs = []
    for filename in os.listdir(directory):
        if not filename.endswith(".txt"):
            continue
        path = os.path.join(directory, filename)
        with open(path, "r", encoding="utf-8") as f:
            text = f.read().strip()
        docs.append({
            "text": text,
            "metadata": {
                "source": filename,
                "doc_type": "requirement"
            }
        })
    return docs
