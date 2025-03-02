#############################################
# main_terraform_gcloud.tf - Terraform Configuration for GCP
#############################################

provider "google" {
  project = var.project
  region  = var.region
  # Optional: Specify your credentials file if not using Application Default Credentials
  # credentials = file("path/to/your/credentials.json")
}

variable "project" {
  description = "Your Google Cloud project ID"
  type        = string
  default     = "cedar-dogfish-451602-u0"
}

variable "region" {
  description = "Google Cloud region"
  type        = string
  default     = "us-east1"
}

variable "zone" {
  description = "Google Cloud zone"
  type        = string
  default     = "us-east1-b"
}

variable "network" {
  description = "VPC network name"
  type        = string
  default     = "default"
}

variable "subnetwork" {
  description = "Subnetwork name"
  type        = string
  default     = "default"
}

variable "machine_type" {
  description = "Compute Engine machine type"
  type        = string
  default     = "f1-micro"
}

# Firewall rule to allow SSH (22), HTTP (80), and HTTPS (443) traffic
resource "google_compute_firewall" "web_fw" {
  name    = "brainboost-fw"
  network = var.network

  allow {
    protocol = "tcp"
    ports    = ["22", "80", "443"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["web-allow"]
}

# Compute Engine instance using Ubuntu 22.04 LTS
resource "google_compute_instance" "web_server" {
  name         = "brainboost-server"
  machine_type = var.machine_type
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = "projects/ubuntu-os-cloud/global/images/family/ubuntu-2204-lts"
      size  = 15
      type  = "pd-ssd"
    }
  }

  network_interface {
    network    = var.network
    subnetwork = var.subnetwork
    access_config {}  # Allocates a public IP
  }

  # Using a non-literal heredoc and escaping $ signs so that Terraform does not interpolate them.
  metadata = {
    "startup-script" = <<EOT
#!/bin/bash
set -ex
LOGFILE="/var/log/startup.log"
echo "=== Startup script initiated at $$(date) ===" >> $${LOGFILE}
echo "Updating system packages..." >> $${LOGFILE}
apt-get update -y >> $${LOGFILE} 2>&1
echo "Installing required packages (rclone, git, curl, build-essential, python3, pip, venv)..." >> $${LOGFILE}
apt-get install -y rclone git curl build-essential python3 python3-pip python3-venv >> $${LOGFILE} 2>&1
echo "Installing Node.js version 18..." >> $${LOGFILE}
curl -sL https://deb.nodesource.com/setup_18.x | bash - >> $${LOGFILE} 2>&1
apt-get install -y nodejs >> $${LOGFILE} 2>&1
cd /home/ubuntu || exit
echo "Cloning repository from GitHub..." >> $${LOGFILE}
if [ ! -d "brainboost_data_source_package" ]; then
  sudo -u ubuntu git clone https://github.com/PabloBorda/brainboost_data_source_package.git >> $${LOGFILE} 2>&1
else
  echo "Repository already exists, updating..." >> $${LOGFILE}
  cd brainboost_data_source_package || exit
  sudo -u ubuntu git pull >> $${LOGFILE} 2>&1
fi
chown -R ubuntu:ubuntu /home/ubuntu/brainboost_data_source_package
echo "Creating Python virtual environment and installing dependencies..." >> $${LOGFILE}
sudo -u ubuntu bash -c "cd /home/ubuntu/brainboost_data_source_package && python3 -m venv myenv && source myenv/bin/activate && pip3 install -r requirements.txt" >> $${LOGFILE} 2>&1
echo "Running media_download.py in background (if available)..." >> $${LOGFILE}
sudo -u ubuntu bash -c "cd /home/ubuntu/brainboost_data_source_package && source myenv/bin/activate && nohup python3 media_download.py --no-user-interaction > media_download.log 2>&1 &" >> $${LOGFILE} 2>&1
echo "Installing Node.js dependencies and building application (if applicable)..." >> $${LOGFILE}
sudo -u ubuntu bash -c "cd /home/ubuntu/brainboost_data_source_package && export NODE_OPTIONS='--max_old_space_size=4096' && npm install && npm run build" >> $${LOGFILE} 2>&1
echo "Starting application server (server.js) if applicable..." >> $${LOGFILE}
nohup node /home/ubuntu/brainboost_data_source_package/server.js > /home/ubuntu/brainboost_data_source_package/server.log 2>&1 &
SERVER_PID=$$!
disown -h $${SERVER_PID}
echo "=== Startup script completed at $$(date) ===" >> $${LOGFILE}
EOT
  }

  tags = ["web-allow"]

  labels = {
    env = "dev"
  }
}

# Output the external IP address of the instance
output "instance_ip" {
  description = "Public IP of the instance"
  value       = google_compute_instance.web_server.network_interface[0].access_config[0].nat_ip
}
