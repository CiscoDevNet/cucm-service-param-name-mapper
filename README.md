# cucm-service-param-name-mapper

## Overview

Sample script that scrapes Cisco Unified Communications Manager admin UI pages to map service parameter UI labels with their programmatic IDs.

Results are output to JSON and markdown formatted files.  Example JSON output files for CUCM versions [12.5(1)SU6](output_v12.51SU6.json)/ [14](output_v14.json) / [14SU3](output_v14SU3.json) are included.

![Screen Shot](images/screen_shot.png)

Uses:

* [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/) for HTML screen scraping.
* [AXL SOAP](https://developer.cisco.com/site/axl/) to retrieve the CUCM process node UUID.

**Tested with:**

* Ubuntu 23.04
* Python 3.11.4
* CUCM 12.5(1)SU6 / 14 / 14SU3

DevNet sandboxes with CUCM instances are available for testing, e.g. **Collaboration / Collaboration 14.0**: [DevNet Sandboxes](https://developer.cisco.com/site/sandbox/)

## Pre-requisites

* Python 3.8+
* CUCM admin UI user credentials, with AXL read permissions

## Getting started

* Create/activate a Python virtual environment, e.g.:

  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

* Install needed dependency packages:

  ```bash
  pip install -r requirements.txt
  ```

* Rename `.env_example` to `.env`, and edit to specify your CUCM host address and admin/AXL credentials.


  > **Notes:**
    > * CUCM hostname is case sensitive - as appears in CUCM admin **List / Server**.
    > * The CUCM admin user must have AXL read permission.

  Be sure to save the file!
  
* To run the sample, use the following command:

  ```bash
  python map_param_names.py
  ```
 
  or if editing the project in Visual Studio Code, just press **F5**

 ## Caveats

* This sample is likely to work against any fairly recent CUCM version - however, as it is implemented via scraping of HTML pages, cosmetic changes to the admin UI service parameter pages (which could happen for any major/minor/SU/ES version) may break parsing.

* Authentication to the CUCM admin pages is automated by simulating a browser-based login sequence - this can fail unexpectedly, e.g. if the script is run multiple times in quick succession or if the admin user is also logged into the site via an actual browser.

  Logging out of the browser session, or just waiting several minutes for the login session to expire should workaround the issue.
  
  See the [Cisco Unified Communications Manager Administration Guide](https://www.cisco.com/c/en/us/td/docs/voice_ip_comm/cucm/admin/10_0_1/ccmcfg/CUCM_BK_C95ABA82_00_admin-guide-100/CUCM_BK_C95ABA82_00_admin-guide-100_chapter_01.html#CUCM_RF_W6916DC4_00):

  ![Security Error](images/security_error.png)