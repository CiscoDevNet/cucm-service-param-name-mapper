import sys
import os
import re
import json
from bs4 import BeautifulSoup
import requests
import urllib3

# Read environment variables from .env
from dotenv import load_dotenv

load_dotenv(override=True)
cucm_hostname = os.getenv("CUCM_HOSTNAME")
cucm_admin_user = os.getenv("CUCM_ADMIN_USER")
cucm_admin_password = os.getenv("CUCM_ADMIN_PASSWORD")

# Disable cosmetic warnings about insecure HTTPS connections
urllib3.disable_warnings()

# Retrieve the CUCM host's AXL version
print("\nRetrieving AXL version: ", end="")
headers = {
    "Content-Type": "text/xml",
}
payload = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ns="http://www.cisco.com/AXL/API/1.0">
   <soapenv:Header/>
   <soapenv:Body>
      <ns:getCCMVersion/>
   </soapenv:Body>
</soapenv:Envelope>"""
try:
    response = requests.post(
        url=f"https://{cucm_hostname}:8443/axl/",
        headers=headers,
        auth=requests.auth.HTTPBasicAuth(cucm_admin_user, cucm_admin_password),
        data=payload,
        verify=False,
    )
    response.raise_for_status()
except Exception as err:
    print(f"\n-->Error retrieving AXL version: {err} ")
    sys.exit(1)
axl_version = ".".join(
    re.search(".*<version>(.*)</version>.*", response.text).group(1).split(".")[0:2]
)
print(axl_version)

# Lookup the CUCM host process node UUID
print("Looking up CUCM host process node UUID: ", end="")

headers = {
    "Content-Type": "text/xml",
    "SOAPAction": f'"CUCM:DB ver={axl_version} listProcessNode"',
}
payload = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ns="http://www.cisco.com/AXL/API/{axl_version}">
   <soapenv:Header/>
   <soapenv:Body>
      <ns:listProcessNode sequence="11">
         <searchCriteria>
            <name>{cucm_hostname}</name>
         </searchCriteria>
         <returnedTags>
            <name></name>
            <description></description>
            <mac></mac>
            <ipv6Name></ipv6Name>
            <nodeUsage></nodeUsage>
            <lbmHubGroup></lbmHubGroup>
            <processNodeRole></processNodeRole>
         </returnedTags>
      </ns:listProcessNode>
   </soapenv:Body>
</soapenv:Envelope>"""
try:
    response = requests.post(
        url=f"https://{cucm_hostname}:8443/axl/",
        headers=headers,
        auth=requests.auth.HTTPBasicAuth(cucm_admin_user, cucm_admin_password),
        data=payload,
        verify=False,
    )
except Exception as err:
    print(f"\n-->Error looking up host process node UUID: {err} ")
    sys.exit(1)
if re.search('.*uuid="{(.*)}".*', response.text) is None:
    print(f"\n-->Error: process node not found: {cucm_hostname}")
    sys.exit(1)
cucm_process_node_uuid = re.search('.*uuid="{(.*)}".*', response.text).group(1).lower()
print(cucm_process_node_uuid)

# Submit the admin login form with credentials
# Use requests.Session to retain the resulting login cookies for re-use
print("Logging into the admin site: ", end="")
session = requests.Session()
payload = (
    f"appNav=ccmadmin&j_username={cucm_admin_user}&j_password={cucm_admin_password}"
)
headers = {"Content-Type": "application/x-www-form-urlencoded"}
response = session.request(
    "POST",
    url=f"https://{os.getenv('CUCM_HOSTNAME')}/ccmadmin/j_security_check",
    headers=headers,
    data=payload,
    verify=False,
)
print("Done")

# Scrape the list of service indexes from the Service Parameter Configuration page
print("\nScraping list of service indexes: ", end="")
response = session.request(
    "POST",
    url=f"https://{os.getenv('CUCM_HOSTNAME')}/ccmadmin/serviceParamEdit.do?server={cucm_process_node_uuid}&service=-1",
    headers=headers,
    data=payload,
    verify=False,
)
doc = BeautifulSoup(response.text, "html.parser")
if doc.find(id="SERVICE") is None:
    print("Error: failed (possibly due to authentication problems).")
    sys.exit(1)
service_indexes = []
for option in doc.find(id="SERVICE").find_all("option"):
    if option["value"] != "-1":
        service_indexes.append(option)
print("Done")


# Parse service parameters/labels from the admin pages
def parse_params(service_index, service_name):
    service_param_map = {"service": service_name, "parameters": []}
    url = f"https://{cucm_hostname}/ccmadmin/serviceParamEdit.do?server={cucm_process_node_uuid}&service={service_index}"
    response = session.request(
        "POST", url=url, headers=headers, data=payload, verify=False
    )
    doc = BeautifulSoup(response.text, "html.parser")
    # It happens that table rows with a CSS like "content-form-stripe-.*" are all/only params
    param_rows = doc.find_all("tr", class_=re.compile("content-form-stripe-.*"))
    for row in param_rows:
        columns = row.find_all("td")
        # Find the first input element
        input_tag = columns[1].find(["input", "select", "textarea"])
        # If the first input element is type=hidden, this is a display-only param with no corresponding Id - skip
        if "type" in input_tag.attrs and input_tag["type"] == "hidden":
            continue
        param_id = input_tag["id"]
        label = columns[0].label.a.string.strip()
        service_param_map["parameters"].append({"id": param_id, "label": label})
    return service_param_map


print("Parsing service parameters...")
print("* Enterprise Wide ".ljust(60) + ": ", end="")
# Global dictionary for collecting label/parameter mapping objects
label_param_map = []
# Enterprise Wide service index happens to be 11
label_param_map.append(parse_params(service_index="11", service_name="Enterprise Wide"))
print(len(label_param_map[0]["parameters"]))

# Loop through the list service indexes, and parse the params page for each
for index in service_indexes:
    print(f"* {index.text}".ljust(60) + ": ", end="")
    service_params = parse_params(service_index=index["value"], service_name=index.text)
    count = len(service_params["parameters"])
    label_param_map.append(service_params)
    print(count)

print("Writing JSON output: ", end="")
with open("output.json", "w") as file:
    file.write(json.dumps(label_param_map, indent=2))
print("output.json")

print("Writing markdown output: ", end="")
with open("output.md", "w") as file:
    file.write(f"# Service Parameter Label to ID Mapping\n\n")
    file.write(f"**Hostname:** {cucm_hostname}\n\n")
    file.write(f"**AXL Version:** {axl_version}\n\n")
    file.write(
        f"| {'Service'.ljust(60)} | {'Parameter ID'.ljust(50)} | {'Label'.ljust(81)} |\n"
    )
    file.write(f"| {'-'*60} | {'-'*50} | {'-'*81} |\n")
    for service in label_param_map:
        file.write(f"| {service['service'].ljust(60)} | {' '*50} | {' '*81} |\n")
        for parameter in service["parameters"]:
            file.write(
                f"| {''.ljust(60)} | {parameter['id'].ljust(50)} | {parameter['label'].ljust(81)} |\n"
            )
print("output.md")
