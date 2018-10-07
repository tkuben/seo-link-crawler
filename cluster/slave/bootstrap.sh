#!/usr/bin/env bash
echo Provisioning started...........

MASTER_IP="192.168.30.10"
MASTER_HOSTNAME="hadoop-master"
USER="vagrant"

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


#sudo apt-get -y install python2.7 python-pip
#pip install virtualenv
#pip install virtualenvwrapper

sudo apt-get -y install subversion
sudo sh -c 'echo "192.168.30.10     hadoop-master" >> /etc/hosts'



su - $USER << EOF
    echo "Checking out Repository"
    git clone https://github.com/tkuben/seo-link-crawler.git crawler
    chmod 600 ~/crawler/cluster/master/id_dsa

    echo "Setting up passwordless login"
    rm -Rf ~/.ssh/id_*
    ssh-keygen -t dsa -P '' -f ~/.ssh/id_dsa
    cat ~/.ssh/id_dsa.pub >> ~/.ssh/authorized_keys
    cat ~/crawler/cluster/master/id_dsa.pub >> ~/.ssh/authorized_keys
    cat ~/.ssh/id_dsa.pub | ssh -i ~/crawler/cluster/master/id_dsa -oStrictHostKeyChecking=no $USER@$MASTER_HOSTNAME 'cat >> .ssh/authorized_keys'

    echo "Setting up Hadoop"
    scp -oStrictHostKeyChecking=no $MASTER_IP:~/hadoop-2.5.1.tar.gz ./
    #wget http://apache.mirror.rafal.ca/hadoop/common/hadoop-2.5.1/hadoop-2.5.1.tar.gz
    tar -zxvf hadoop-2.5.1.tar.gz
    sudo cp -Rp hadoop-2.5.1 /usr/local/
    sudo chown -R vagrant:vagrant hadoop-2.5.1/
    sudo ln -s /usr/local/hadoop-2.5.1 /usr/local/hadoop
    sudo sh -c 'echo "export HADOOP_HOME=/usr/local/hadoop/" >> /etc/bash.bashrc'
    sudo sh -c 'echo alias h=\"cd /usr/local/hadoop/\" >> /etc/bash.bashrc'


    echo "Setting up Java"
    scp -oStrictHostKeyChecking=no $MASTER_IP:~/jdk-7u15-linux-x64.gz ./
    tar -zxvf jdk-7u15-linux-x64.gz
    sudo mv jdk1.7.0_15 /usr/local/lib/
    sudo ln -s /usr/local/lib/jdk1.7.0_15 /usr/local/lib/java
    sudo sh -c 'echo "export JAVA_HOME=/usr/local/lib/java/" >> /etc/bash.bashrc'
    sudo sh -c 'echo "export PATH=$PATH:/usr/local/lib/java/bin:/usr/local/hadoop/bin:/usr/local/hadoop/sbin" >> /etc/bash.bashrc'

    . /etc/bash.bashrc
    sudo sed -i 's#\${JAVA_HOME}#/usr/local/lib/java#' /usr/local/hadoop/etc/hadoop/hadoop-env.sh
    sudo sed -i 's#Java parameters#\nexport JAVA_HOME=/usr/local/lib/java#' /usr/local/hadoop/etc/hadoop/yarn-env.sh

    mkdir ~/virtualenvs


    #COPYING file to dynamically set the hostname/ip by sudo
    scp hadoop-master:/usr/local/hadoop/etc/hadoop/slaves ~/

EOF


last_node_number=`tail -1 /home/vagrant/slaves | awk -F'-' '{print $3}'`
if [ -z "$last_node_number" ]
then
    last_node_number=10
fi


echo "Last Node Number: ${last_node_number}"
current_node_number=$((last_node_number+1))
ip="192.168.30.${current_node_number}"
hostname="hadoop-node-${current_node_number}"
echo "Setting Hostname to ${hostname}, IP: ${ip}"
echo $hostname > hostname
sudo mv hostname /etc/hostname
sudo sed -i "s#192.168.30.200#${ip}#" /etc/network/interfaces
sudo sed -i "s#hadoop-node#hadoop-node-${current_node_number}#" /etc/hosts
sudo /etc/init.d/networking restart


su - $USER << EOF
    cat /etc/hostname | ssh -i /home/vagrant/crawler/cluster/master/id_dsa -oStrictHostKeyChecking=no $USER@$MASTER_HOSTNAME 'cat >> /usr/local/hadoop/etc/hadoop/slaves'
    echo "${ip}     ${hostname}" | ssh -i /home/vagrant/crawler/cluster/master/id_dsa -oStrictHostKeyChecking=no $USER@$MASTER_HOSTNAME 'cat >> /etc/hosts'
EOF

sudo reboot