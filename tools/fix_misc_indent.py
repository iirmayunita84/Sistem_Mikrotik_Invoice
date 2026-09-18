path = r"D:\mikrotik_invoice\routes\misc_routes.py"

with open(path,"r",encoding="utf-8") as f:
    lines=f.readlines()


fixed=[]

for line in lines:
    if line.startswith("    ") and not line.startswith("        "):
        if line.lstrip().startswith(("from ","import ")):
            line=line.lstrip()

    fixed.append(line)


with open(path,"w",encoding="utf-8") as f:
    f.writelines(fixed)


print("misc_routes indent fixed")