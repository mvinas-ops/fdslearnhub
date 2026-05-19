from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .auth import hash_password
from .models import Permission, Role, RolePermission, User, Barangay, TrainingMaterial, Lesson, Resource, Schedule, ScheduleParticipant, CMLBarangay, SessionMaterialMapping
from .utils import normalize_slug
from datetime import date

PERMISSIONS = [
    "view_training_materials","view_profile","receive_notifications","create_schedules",
    "manage_participants","view_attendance","send_notifications","download_reports",
    "manage_users","manage_training_materials","manage_roles","manage_session_material_mapping","full_access"
]

async def get_or_create(db: AsyncSession, model, defaults=None, **filters):
    obj = (await db.execute(select(model).filter_by(**filters))).scalar_one_or_none()
    if obj:
        return obj
    obj = model(**filters, **(defaults or {}))
    db.add(obj)
    await db.flush()
    return obj

async def seed_database(db: AsyncSession):
    perms = {}
    for key in PERMISSIONS:
        perms[key] = await get_or_create(db, Permission, key=key, defaults={"name": key.replace("_", " ").title(), "module": key.split("_")[-1]})

    role_defs = {
        "trainee": ["view_training_materials","view_profile","receive_notifications"],
        "cml": ["create_schedules","manage_participants","view_attendance","send_notifications","download_reports"],
        "administrator": ["full_access"],
    }
    roles = {}
    for slug, pkeys in role_defs.items():
        roles[slug] = await get_or_create(db, Role, slug=slug, defaults={"name": "CML (Community Leader)" if slug=="cml" else slug.replace("_"," ").title(), "description": f"System {slug} role", "color": "purple" if slug=="administrator" else "green" if slug=="cml" else "blue", "is_system_role": True})
        for key in pkeys:
            exists = (await db.execute(select(RolePermission).where(RolePermission.role_id==roles[slug].id, RolePermission.permission_id==perms[key].id))).scalar_one_or_none()
            if not exists:
                db.add(RolePermission(role_id=roles[slug].id, permission_id=perms[key].id))

    bgy_a = await get_or_create(db, Barangay, name="Barangay A", defaults={"psgc":"0137401001"})
    bgy_b = await get_or_create(db, Barangay, name="Barangay B", defaults={"psgc":"0137401002"})
    bgy_c = await get_or_create(db, Barangay, name="Barangay C", defaults={"psgc":"0137401003"})

    async def make_user(email, full_name, role_slug, barangay=None, phone=None):
        user = (await db.execute(select(User).where(User.email==email))).scalar_one_or_none()
        if user:
            return user
        user = User(email=email, password=hash_password("password"), full_name=full_name, role=role_slug, role_id=roles[role_slug].id, barangay_id=barangay.id if barangay else None, phone=phone, psgc=barangay.psgc if barangay else None, status="active", is_active=True)
        db.add(user); await db.flush(); return user

    admin = await make_user("admin@learnhub.com", "Administrator", "administrator")
    cml = await make_user("cml@learnhub.com", "Community Leader", "cml")
    john = await make_user("john@example.com", "John Smith", "trainee", bgy_a, "+63 912 345 6789")
    sarah = await make_user("sarah@example.com", "Sarah Johnson", "trainee", bgy_b)
    maria = await make_user("maria@example.com", "Maria Garcia", "trainee", bgy_a)
    for b in [bgy_a,bgy_b,bgy_c]:
        if not (await db.execute(select(CMLBarangay).where(CMLBarangay.cml_user_id==cml.id, CMLBarangay.barangay_id==b.id))).scalar_one_or_none():
            db.add(CMLBarangay(cml_user_id=cml.id, barangay_id=b.id))

    mats = [
        ("Web Development Course", "Master the fundamentals of modern web development", "Development", 12, "6 hours"),
        ("Advanced React Patterns", "Level up React skills with advanced patterns and techniques", "Development", 8, "4.5 hours"),
        ("TypeScript Deep Dive", "Comprehensive TypeScript training from basics to advanced", "Development", 10, "5 hours"),
        ("UI/UX Design Fundamentals", "Learn the principles of creating great user experiences", "Design", 15, "7.5 hours"),
        ("Figma Professional", "Master Figma professional design workflow", "Design", 6, "3 hours"),
        ("Programming Basics", "Start your programming journey with fundamentals", "Development", 8, "4 hours"),
        ("Python Fundamentals", "Learn Python programming from scratch", "Development", 12, "6 hours"),
    ]
    material_objs=[]
    for title, desc, cat, lessons, dur in mats:
        material_objs.append(await get_or_create(db, TrainingMaterial, slug=normalize_slug(title), defaults={"title":title,"description":desc,"category":cat,"number_of_lessons":lessons,"total_duration":dur,"status":"active","created_by_id":admin.id}))
    web = material_objs[0]
    lesson_titles = ["Introduction to HTML","CSS Fundamentals","JavaScript Basics","DOM Manipulation","Responsive Design","CSS Grid & Flexbox","Introduction to APIs","Async JavaScript"]
    for i,title in enumerate(lesson_titles, start=1):
        if not (await db.execute(select(Lesson).where(Lesson.material_id==web.id, Lesson.lesson_number==i))).scalar_one_or_none():
            db.add(Lesson(material_id=web.id, lesson_number=i, title=title, duration_minutes=[25,30,45,35,40,30,25,35][i-1], order_index=i))
    for fname, ftype, size in [("Course Handbook.pdf","pdf",2400000),("Code Examples.zip","zip",1800000),("Cheat Sheet.pdf","pdf",856000)]:
        if not (await db.execute(select(Resource).where(Resource.material_id==web.id, Resource.file_name==fname))).scalar_one_or_none():
            db.add(Resource(material_id=web.id, file_name=fname, stored_file_name=fname, file_type=ftype, file_size=size, file_path=None, uploaded_by_id=admin.id))

    sched = await get_or_create(db, Schedule, session_title="Web Development Fundamentals", defaults={"material_id":web.id,"session_date":date(2026,3,15),"session_time":"09:00","location":"Community Center - Barangay A","barangay_id":bgy_a.id,"status":"upcoming","created_by_id":cml.id})
    for u, st in [(john,"attended"),(maria,"attended")]:
        if not (await db.execute(select(ScheduleParticipant).where(ScheduleParticipant.schedule_id==sched.id, ScheduleParticipant.user_id==u.id))).scalar_one_or_none():
            db.add(ScheduleParticipant(schedule_id=sched.id, user_id=u.id, attendance_status=st))
    for m in [web, material_objs[5]]:
        if not (await db.execute(select(SessionMaterialMapping).where(SessionMaterialMapping.session_id==sched.id, SessionMaterialMapping.material_id==m.id))).scalar_one_or_none():
            db.add(SessionMaterialMapping(session_id=sched.id, material_id=m.id))
    await db.commit()
