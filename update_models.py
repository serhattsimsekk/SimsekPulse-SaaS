import re

with open("database/models.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

models_needing_tenant = {
    "DriverDocument": True,
    "DisciplineRecord": True,
    "TachographViolation": True,
    "RestBreak": True,
    "VehicleTrailerAssignment": True,
    "DriverTask": True,
    "ShiftHandover": True,
    "Waybill": True,
    "WeighbridgeTicket": True,
    "WaitEvent": True,
    "MaintenanceIssue": True,
    "WorkOrder": True,
    "PartMovement": True,
    "Inspection": True,
    "FuelTransaction": True,
    "TelemetryEvent": True,
    "GeofenceEvent": True,
    "Tire": True,
    "Incident": True,
    "SupplierSettlement": True,
    "BackupRun": False,
}

new_lines = []
current_class = None
inside_target_class = False

for i, line in enumerate(lines):
    new_lines.append(line)
    
    # Check class declaration
    class_match = re.match(r"^class\s+(\w+)\(", line)
    if class_match:
        current_class = class_match.group(1)
        if current_class in models_needing_tenant:
            inside_target_class = True
        else:
            inside_target_class = False
            
    # Check __tablename__
    if inside_target_class and "__tablename__" in line:
        is_req = models_needing_tenant[current_class]
        if is_req:
            field_line = '    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)\n'
        else:
            field_line = '    tenant_id: Mapped[str | None] = mapped_column(ForeignKey("tenants.id"), index=True)\n'
        new_lines.append(field_line)
        print(f"Inserted tenant_id into {current_class}")
        inside_target_class = False

content = "".join(new_lines)

# Ensure company_id synonym in all classes with tenant_id
classes = re.findall(r"class\s+(\w+)\([^)]+\):", content)
for c in classes:
    if c == "Tenant":
        continue
    # Check if class has tenant_id but not company_id synonym
    class_regex = rf"(class\s+{c}\([^)]+\):[\s\S]+?)(?=\nclass\s+|\Z)"
    m = re.search(class_regex, content)
    if m:
        block = m.group(1)
        if "tenant_id" in block and "company_id = synonym" not in block:
            new_block = block.rstrip() + '\n    company_id = synonym("tenant_id")\n\n'
            content = content.replace(block, new_block)
            print(f"Added company_id synonym to {c}")

with open("database/models.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Models update finished successfully!")
