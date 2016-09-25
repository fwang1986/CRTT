#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os,sys,time,argparse,commands,pexpect
import re

# target PC info
IP_TARGET = '10.100.7.10'
USER = 'fei_wang'
PASS = 'fw'

class sshtoremote:

    def __init__(self, user, ip, passwd):
        self.user = user
        self.ip = ip
        self.passwd = passwd
        self.connect = False

    '''
    # ssh to the target PC
    '''
    def sshto(self):
        rc = 0
        sshcmd = 'ssh %s@%s'%(self.user, self.ip)
        child = pexpect.spawn(sshcmd)
        index = child.expect(['(?i)Password:', 'continue connecting (yes/no)?', pexpect.EOF, pexpect.TIMEOUT],timeout=60)
        if index == 0:
            child.sendline(self.passwd)
            index2 = child.expect(['(?i)Last login:', '(?i)Permission', pexpect.EOF, pexpect.TIMEOUT], timeout=60)
        elif index == 1:
            child.sendline('yes')
            try:
                child.expect('(?i)password')
            except pexpect.EOF:
                print "ssh error: EOF"
                return -1
            except pexpect.TIMEOUT:
                print "ssh error: TIMEOUT"
                return -2
            child.sendline(self.passwd)
            index2 = child.expect(['(?i)Last login', '(?i)Permission', pexpect.EOF, pexpect.TIMEOUT], timeout=60)
        else:
            print "Failure: ssh failed, please check if %s is online!"%(self.ip)
            return -3
        if index2 == 0:
            self.connect = True
            self.child = child
        elif index2 == 1:
            print "Failure: ssh permission denied, please check if the %s existed or the password is correct!"%(self.user)
            return -4
        else:
            print "Failure: ssh failed, Unknown error!"
            return -5
        print 'ssh to %s@%s success'%(self.user, self.ip)
        return rc

    '''
    # send command to remote PC and judge the expect content by comparing the 
    # return content with the param expectcontent, default timeout is 5S.
    '''
    def sshcmdsend(self, cmd, expectcontent, tmout=5):
        index = 0
        if self.connect:
            self.child.sendline(cmd)
            index = self.child.expect([expectcontent, pexpect.EOF, pexpect.TIMEOUT], timeout=tmout)
        else:
            print 'connection not setup, please check ssh connention!'
            index = -1
        return index

    '''
    # scp local file/path to remote path &
    # scp remote file/path to local path
    #
    #    scp local file/path to remotepath, ispath is a flag to indicate the local is path/file
    #    
    #    notice:
    #      1. file/path name should use '\' for the charecter ' ' and '$'.
    #      2. also scp local user@ip:'remote' cmd to avoid non-nessary error.
    #      3. the remote must with the charecter ' and \ to avoid error resulted by special character.
    #
    '''
    def scpwithremote(self, local, remote, ispath=0, tolocal=0):
        rc = 0
        local = local.replace(' ','\ ')
        local = local.replace('$','\$')
        remote = remote.replace(' ','\ ')
        remote = remote.replace('$','\$')
        # is it a path
        if ispath == 0:
            # scp to remote
            if tolocal == 0:
                scpcmd = 'scp %s %s\@%s\:\'%s\''%(local, self.user, self.ip, remote)
                print 'scp file %s to remote %s'%(local, remote)
            # scp to local
            else:
                scpcmd = 'scp %s\@%s\:\'%s\' %s'%(self.user, self.ip, remote, local)
                print 'scp file %s to local %s'%(remote, local)

        else:
            # scp to remote
            if tolocal == 0:
                scpcmd = 'scp -r %s %s\@%s\:\'%s\''%(local, self.user, self.ip, remote)
                print 'scp dir %s to remote %s'%(local, remote)
            # scp to local
            else:
                scpcmd = 'scp -r %s\@%s\:\'%s\' %s'%(self.user, self.ip, remote, local)
                print 'scp dir %s to local %s'%(remote, local)
        scpchild = pexpect.spawn(scpcmd)
        index = scpchild.expect(['(?i)Password:', 'continue connecting (yes/no)?', pexpect.EOF, pexpect.TIMEOUT],timeout=300)
        if index == 0:
            scpchild.sendline(self.passwd)
            index2 = scpchild.expect(['100\%', pexpect.EOF, pexpect.TIMEOUT], timeout=300)
            if index2 == 0:
                time.sleep(5)
                if tolocal == 0:
                    print "scp %s to remote %s done!"%(local, remote)
                else:
                    print "scp %s to local %s done!"%(remote, local)
            else:
                rc = 1
                if tolocal == 0:
                    print "scp %s to remote path %s failure, reason: %d"%(local, remote, rc)
                else:
                    print "scp %s to local path %s failure, reason: %d"%(remote, local, rc)
        elif index == 1:
            scpchild.sendline('yes')
            try:
                scpchild.expect('(?i)password')
            except pexpect.EOF:
                print 'ssh error: EOF when scp'
                rc = 2
            except pexpect.TIMEOUT:
                print 'ssh error: TIMEOUT when scp'
                rc = 3
            scpchild.sendline(self.passwd)
            index2 = scpchild.expect(['100\%', pexpect.EOF, pexpect.TIMEOUT], timeout=300)
            if index2 == 0:
                if ispath != 0:
                    time.sleep(15)
                if tolocal == 0:
                    print "scp %s to remote %s done!"%(local, remote)
                else:
                    print "scp %s to local %s done!"%(remote, local)
            else:
                rc = 4
                if tolocal == 0:
                    print "scp %s to remote path %s failure, reason: %d"%(local, remote, rc)
                else:
                    print "scp %s to local path %s failure, reason: %d"%(remote, local, rc)
        else:
            print 'Failure: ssh failed, please check if remote is online!'
    #    scpchild.close(force=True)
        return rc
    

    '''
    # send rm command to remote PC
    #
    #    avoid special character in the filename, delete the file as following step:
    #     rm 'filename' command to delete the file.(this can delete the file with special character in the filename too.)
    #
    '''
    def sshdelfile(self, filename):
        delcmd = 'rm -rf \'%s\''%(filename)
        indexdict = {0:'%s success!'%(delcmd), 1:'%s return EOF!'%(delcmd), 2:'%s TIMEOUT!'%(delcmd), -1:'connection not setup!'}
        index = self.sshcmdsend(delcmd, '%s@'%(self.user), tmout=15)
        if index == 0:
            time.sleep(1)
        return index

    def __del__(self):
        if self.connect:
            self.child.close(force=True)

def main():
    global IP_TARGET
    global USER
    global PASS
    sshclass = sshtoremote(USER, IP_TARGET, PASS)
    sshclass.sshto()
    filename = '/home/fei_wang/$wan 王飞'
    rc = sshclass.sshdelfile(filename)
    if rc == 0:
        print 'Delete OK!'
    local = '/mnt/hgfs/share/pytest/test1/@~$wan 王飞 - 副本 - 副本.docx'
    remotepath = '/home/fei_wang/$wan'
    rc = sshclass.scpwithremote(local, remotepath, ispath=0)
    if rc == 0:
        print 'scp file OK!'
    local = '/mnt/hgfs/share/pytest/test1/@~$wan 王飞 - 副本 - 副本'
    remotepath = '/home/fei_wang/$wan'
    rc = sshclass.scpwithremote(local, remotepath, ispath=1)
    if rc == 0:
        print 'scp dir OK!'
    localpath = './'
    remote = '/home/fei_wang/$wan/@~$wan 王飞 - 副本 - 副本.docx'
    rc = sshclass.scpwithremote(localpath, remote, ispath=0, tolocal=1)
    if rc == 0:
        print 'scp file OK!'
    localpath = './'
    remote = '/home/fei_wang/$wan/@~$wan 王飞 - 副本 - 副本'
    rc = sshclass.scpwithremote(localpath, remote, ispath=1, tolocal=1)
    if rc == 0:
        print 'scp dir OK!'
    time.sleep(1)
        
    return 0

if __name__ == '__main__':
    main()
