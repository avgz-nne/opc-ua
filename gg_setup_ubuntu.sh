#!/bin/bash

# AWS IOT GreengrassDeviceSetup script
# GreengrassDeviceSetup helps to install all the required softwares and creates user and permission to connect this core device with Cloud
# And Creates few basic mandatory components (Nucleus, IPDetector, TokenExchange, etc.) which helps to run other components in this core device
# For more information on this set up please read this AWS documentation on Green Grass set up version 2 
# Documentatio link - https://docs.aws.amazon.com/greengrass/v2/developerguide/what-is-iot-greengrass.html
# This set up can be used only for GreenGrass V2, for GreenGrass V1 Please refer AWS documentation
# After the successful installation this core device will be appear in AWS, IoT Core => Greengrass devices => Core devices 



# User Input Section

read -p "Enter your AWS access key ID: 
" aws_access_key_id

read -p "Enter your AWS secret access key:
" aws_secrete_access_key_id

read -p "Enter the AWS Region where you want to create a Greengrass thing group (ex: eu-central-1):
" region 

read -p "Enter The Thing name of the Greengrass core:
" thing_name 

read -p "Enter a name for the Greengrass Thing group:
" group_name


# Installing Java based on user input

while true; do

read -p "Do you want to intasll Java? (y/n) " yn

case $yn in
	[yY] ) echo Installing Java ......;
        #sudo yum update
        sudo apt install default-jdk
        echo Successfully installed Java on your machine.
        break;;

	[nN] ) echo Skipping Java installation;
	break;;

	* ) echo invalid response;;
esac
done


# Creating system default user and group

echo Creating the default system user and group that runs components on the device:
sudo useradd --system --create-home ggc_user
sudo groupadd --system ggc_group


# Adding permission to the newly created user and grpoup

echo 'root ALL=(ALL:ALL) ALL' | sudo EDITOR='tee -a' visudo


# Setting AWS Credentials for IOT device

export AWS_ACCESS_KEY_ID=$aws_access_key_id
export AWS_SECRET_ACCESS_KEY=$aws_secrete_access_key_id


# Downloading and Installing GreenGrassCore Software

curl -s https://d2s8p88vqu9w66.cloudfront.net/releases/greengrass-nucleus-latest.zip > greengrass-nucleus-latest.zip && unzip greengrass-nucleus-latest.zip -d GreengrassCore
sudo -E java -Droot="/greengrass/v2" -Dlog.store=FILE -jar ./GreengrassCore/lib/Greengrass.jar --aws-region us-east-1 --thing-name $thing_name --thing-group-name $group_name --component-default-user ggc_user:ggc_group --provision true --setup-system-service true --deploy-dev-tools true


# Creating Folders for storing artifacts and recipes of the components

mkdir -p ~/greengrassv2/{recipes,artifacts}



# Editing boot file to support to run containerized lambda as a component

echo 'cgroup_enable=memory cgroup_memory=1 systemd.unified_cgroup_hierarchy=0' > /boot/cmdline.txt

read -p "Your system needs reboot to apply the changes, Do you want to reboot it now ?  (y/n) " yn

while true; do

case $yn in
	[yY] ) echo Rebooting your System ......;
        
        sudo reboot
        break;;

	[nN] ) echo Skipping System reboot, you may need to reboot it later;
	break;;

	* ) echo invalid response;;
esac

done



