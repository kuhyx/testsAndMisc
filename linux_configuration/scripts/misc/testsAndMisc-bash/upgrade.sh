#!/bin/sh
apt-get -y update && apt-get -y upgrade && apt -y dist-upgrade
apt -y autoremove
aptitude -y update && aptitude -y safe-upgrade && aptitude -y dist-upgrade
