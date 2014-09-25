#!/usr/bin/env bash
echo Provisioning started...........

MASTER_IP="192.168.30.10"

sudo apt-get update

sudo apt-get -y install rsync ssh

#sudo apt-get -y install virtualbox-ose-guest-utils virtualbox-ose-guest-x11 virtualbox-ose-guest-dkms

#update time zone to EST
#echo "US/Eastern" | sudo tee /etc/timezone
#sudo dpkg-reconfigure --frontend noninteractive tzdata

#sudo apt-get -y remove dictionaries-common
#sudo apt-get -y install python-software-properties
sudo apt-get -y install vim

#sudo apt-get -y install mysql-server

sudo apt-get -y install python2.7 python-pip
pip install virtualenv
pip install virtualenvwrapper

sudo apt-get -y install subversion

svn co --non-interactive https://supergroupdeals.svn.cvsdude.com/supergroupdeals/other_projects/seo_link_crawler/trunk/cluster --username 'savitha' --password 'lalaFungi2214'

echo "Setting up passwordless login"
ssh-keygen -t dsa -P '' -f ~/.ssh/id_dsa
cat ~/.ssh/id_dsa.pub >> ~/.ssh/authorized_keys
cat ~/cluster/master/id_dsa.pub >> ~/.ssh/authorized_keys
ssh-copy-id $MASTER_IP


echo "Setting up Hadoop"
scp $MASTER_IP:~/hadoop-2.5.1.tar.gz ./
#wget http://apache.mirror.rafal.ca/hadoop/common/hadoop-2.5.1/hadoop-2.5.1.tar.gz
tar -zxvf hadoop-2.5.1.tar.gz
sudo cp -Rp hadoop-2.5.1 /usr/local/
sudo chown -R vagrant:vagrant hadoop-2.5.1/
sudo ln -s /usr/local/hadoop-2.5.1 /usr/local/hadoop
sudo sh -c 'echo "export HADOOP_HOME=/usr/local/hadoop/" >> /etc/bash.bashrc'
sudo sh -c 'echo alias h=\"cd /usr/local/hadoop/\" >> /etc/bash.bashrc'


echo "Setting up Java"
#TODO need to download and setup java
scp $MASTER_IP:~/jdk-7u15-linux-x64.gz ./
tar -zxvf jdk-7u15-linux-x64.gz
sudo mv jdk1.7.0_15 /usr/local/lib/
sudo ln -s /usr/local/lib/jdk1.7.0_15 /usr/local/lib/java
sudo sh -c 'echo "export JAVA_HOME=/usr/local/lib/java/" >> /etc/bash.bashrc'
sudo sh -c 'echo "export PATH=$PATH:/usr/local/lib/java/bin:/usr/local/hadoop/bin:/usr/local/hadoop/sbin" >> /etc/bash.bashrc'

. /etc/bash.bashrc
sudo sed -i 's#${JAVA_HOME}#/usr/local/lib/java#' $HADOOP_HOME/etc/hadoop/hadoop-env.sh
sudo sed -i 's#Java parameters#\nexport JAVA_HOME=/usr/local/lib/java#' $HADOOP_HOME/etc/hadoop/yarn-env.sh


mkdir ~/virtualenvs
