# HyFed - Install
The **HyFed** framework consists of three components: (1) **WebApp**, written in **Angular** (version 10.0) and **HTML/CSS**; (2) **server**, written in **Python** (version 3.6) and based on
the **Django** framework (version 3.1); (3) **client**, written in **Python** (3.6) and based on the **tkinter** package. In the following, we show how to set up 
the development environment for the different components of the **HyFed** framework in Ubuntu 18.04/20.04 LTS.

### All components
Install the **git** and **curl** commands:
   ```
   sudo apt update -y
   sudo apt install curl git -y
   ```

Clone the HyFed GitHub repository into the local machine:
   ```
   git clone https://github.com/TUM-AIMED/hyfed
   ```

### WebApp component
Install **Node.js** and **Angular**:
   ```
    sudo curl -fsSL https://deb.nodesource.com/setup_14.x | sudo -E bash -
    sudo apt install nodejs -y 
    sudo npm install -g @angular/cli@10
   ```

### Client and server components
Install **pip3**, **tkinter**, and **virtualenv**: 
   ```
   sudo apt install python3-pip python3-tk -y
   ```
   ```
   sudo pip3 install virtualenv
   ```
Create the client and server virtual environments:
   ```
   virtualenv -p python3 hyfed-client-venv
   virtualenv -p python3 hyfed-server-venv
   ```

Install the Python packages and their dependencies for the client and server components in the corresponding virtual environments:
   ```
   source hyfed-client-venv/bin/activate
   cd hyfed/hyfed-client
   pip3 install -r requirements.txt
   deactivate
   ```

   ```
   source hyfed-server-venv/bin/activate
   cd hyfed/hyfed-server
   pip3 install -r requirements.txt
   deactivate
   ```
We completed the installation of the **HyFed** framework. Now, we can start: (1) developing our own federated tools using the **HyFed** API 
with the [development tutorial for the Stats tool](develop_hyfed.md) as the guideline, or (2) running **Stats** tool using the instructions outline in [Hyfed-Run](run_hyfed.md) 
to see how the **HyFed** framework works.

