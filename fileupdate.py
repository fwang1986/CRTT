#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os,sys,time,argparse,commands,pexpect
from lib import *
import logging

# debug info
#DEBUG_PRINT = True
DEBUG_PRINT = False

# remote target pathlst and md5filelst
MD5FILELOG = '/tmp/md5checkfilelst.txt'
MD5PATHLOG = '/tmp/md5checkpathlst.txt'

# count of action to file
COPY_COUNT = 0
UPDATAE_COUNT = 0
REMOVE_COUNT = 0

class fileupdate:

    def __init__(self, conffile):
        if os.path.exists(conffile):
            self.conf = conffile
        else:
            print "configure file %s does not existed, use default value!"%(conffile)
        self.user = 'fei_wang'
        self.ip = '10.100.7.10'
        self.passwd = 'fw'
        self.localpath = '/mnt/hgfs/share/pytest/ZSHX_database'
        self.remotepath = '/home/fei_wang/ZSHX_database'
        self.logname = 'fileupdate-log.txt'
        self.logpath = '/var/fileupdate/'
        self.updatecnt = 0
        self.checkcnt = 0

    '''
    # configure file parser
    '''
    def confparser(self):
        conf = configobj.ConfigObj('%s'%(self.conf), encoding='UTF8')
        self.user = conf['remote']['user']
        self.ip = conf['remote']['ip']
        self.passwd = conf['remote']['passwd']
        self.localpath = conf['local']['path']
        self.remotepath = conf['remote']['path']
        self.logname = conf['log']['name']
        self.logpath = conf['log']['path']


    '''
    # log record
    '''
    def setup_logging(self):
        # create a log
        self.logger = logging.getLogger('updatetoremote')
    
        if not os.path.exists(self.logpath):
            os.makedirs(self.logpath)
        handlername = self.logpath+'/'+self.logname
        # create a handler for the log-writing, output into file and console
        handler = logging.FileHandler(handlername)
        console = logging.StreamHandler()
    
        # set the format
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    
        # set the file and console format handler value
        handler.setFormatter(formatter)
        console.setFormatter(formatter)
    
        # add log handler in form of file and console
        self.logger.addHandler(handler)
        self.logger.addHandler(console)
    
        # set the level of log to debug format
        self.logger.setLevel(logging.DEBUG)
        return self.logger

    '''
    # configuration information record to log
    '''
    def confinfotolog(self):
        self.logger.info("="*100)
        self.logger.info('****************  Update local to remote Start  *******************')
        self.logger.info("Configure Info:")
        self.logger.info("-"*100)
        self.logger.info("Local")
        self.logger.info("\tpath: %s"%(self.localpath))
        self.logger.info("Remote")
        self.logger.info("\tpath: %s"%(self.remotepath))
        self.logger.info("\tuser: %s"%(self.user))
        self.logger.info("\tip: %s"%(self.ip))
        starttm = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))
        self.logger.info("start time: %s"%(starttm))
        self.logger.info("-"*100)

    '''
    # ssh to remote
    '''
    def sshwithremote(self):
        retdict = {0:'ssh to %s@%s success!'%(self.user, self.ip),
                   -1:'ssh to %s@%s error, expect EOF!'%(self.user, self.ip),
                   -2:'ssh to %s@%s error, expect TIMEOUT!'%(self.user, self.ip),
                   -3:'ssh to %s@%s failure, check if remote online!'%(self.user, self.ip),
                   -4:'ssh to %s@%s failure, permission denied!'%(self.user, self.ip),
                   -5:'ssh to %s@%s error, unknown error!'%(self.user, self.ip)
                }
        self.sshclass = sshgetremote.sshtoremote(self.user, self.ip, self.passwd)
        rc = self.sshclass.sshto()
        if rc == 0:
            self.logger.info("%s"%(retdict[rc]))
        else:
            self.logger.info("%s"%(retdict[rc]))
        return rc

    '''
    # local md5 checkout, return the md5sum result
    '''
    def localmd5file(self, file_local):
        sumresult = 'none'
        md5cmd = 'md5sum \'%s\''%(file_local)
        md5cmd = md5cmd.encode('utf-8')
        sta, out = commands.getstatusoutput(md5cmd)
        if sta != 0:
            self.logger.error("MD5 of local file Failure: \"%s\""%(out))
        else:
            sumresult = out.split(' ')[0]
        return sumresult

    '''
    # remote md5 checkout, return the md5sum list of all files result located at path_to
    '''
    def remotemd5filegenerate(self):
        rc = 0
        global MD5FILELOG
        global MD5PATHLOG
        self.logger.info("Start generating MD5 check files of remote...")
        self.logger.info("scp local remotemd5.py to remote!")
        rc = self.sshclass.scpwithremote('remotemd5.py', '/tmp')
        if rc != 0:
            self.logger.error('scp remotemd5.py file to remote error, error code:%d'%(rc))
            return rc

        md5filecmd = 'python /tmp/remotemd5.py -c %s'%(self.remotepath)
        self.sshclass.child.sendline(md5filecmd)
        index = self.sshclass.child.expect(['done', 'not exist', 'failure', pexpect.EOF, pexpect.TIMEOUT], timeout=7200)
        if index == 0:
            self.logger.info("MD5 file of remote create success!")
            rc = self.sshclass.scpwithremote('/tmp', MD5FILELOG, ispath=0, tolocal=1)
            if rc != 0:
                self.logger.error("scp %s to local failure, error code: %d!"%(MD5FILELOG,rc))
                return rc
            rc = self.sshclass.scpwithremote('/tmp', MD5PATHLOG, ispath=0, tolocal=1)
            if rc != 0:
                self.logger.error("scp %s to local failure, error code: %d!"%(MD5PATHLOG,rc))
                return rc
        elif index == 1:
            self.logger.error("The remote path %s does not exist!"%(self.remotepath))
        else:
            self.logger.error("MD5 file of remote create Failure!")
        return index

    '''
    # update contents of local to remote
    # return code(rc)
        0 --- success
        non-zero --- failure
    '''
    def pathwalkupdate(self):
        rc = 0
        global DEBUG_PRINT
        global MD5FILELOG
        global MD5PATHLOG
        dircopycnt = 0  # count of copy dirs
        filecopycnt = 0  # count of copy files
        fileupdatecnt = 0  # count of update files
        filedelcnt = 0  # count of del files
        listdir_local = os.walk(self.localpath)
        fd1 = open(MD5PATHLOG, 'r')
        pathlst = fd1.readlines()
        fd2 = open(MD5FILELOG, 'r')
        filelst = fd2.readlines()
        self.logger.info('Start to Updating...')
        for root_local, dir_local, file_local in listdir_local:
            for dirname in dir_local:
                pfind_flag = 0    # find path flag
                local_child_dir = os.path.join(root_local, dirname)
                remote_child_dir = local_child_dir.replace(self.localpath,self.remotepath,1)
                for path_remote in pathlst:
                    # unicode translate
                    upath_remote = unicode(path_remote, 'utf-8')
                    path_cmp = upath_remote.replace('\n','')
                    if remote_child_dir == path_cmp:
                        pathlst.remove(path_remote)
                        pfind_flag = 1
                        pass
    
                # mkdir if not find in remotepathlst file
                if pfind_flag == 0:
                    dircopycnt += 1  # increase count of copy dirs
                    ispath = 1
                    remote_child_dir = remote_child_dir.replace(' ','\ ')
                    remote_child_dir = remote_child_dir.replace('$','\$')
                    mkdircmd = 'mkdir -p '+remote_child_dir
                    self.logger.info('mkdircmd: %s'%(mkdircmd))
                    self.sshclass.child.sendline(mkdircmd)
                    time.sleep(1)
                    
            for filename in file_local:
                ffind_flag = 0    # file find flag
                local_child_file = os.path.join(root_local, filename)
                remote_child_file = local_child_file.replace(self.localpath,self.remotepath,1)
                root_remote = root_local.replace(self.localpath,self.remotepath,1)
                for file_remote in filelst:
                    # unicode translate
                    ufile_remote = unicode(file_remote, 'utf-8')
                    file_cmp = ufile_remote.split(':')[0]
                    md5_remote = file_remote.split(':')[1]
                    md5_remote = md5_remote.split('\n')[0]
                    # if find in the filelst, md5 it and compare with the local file
                    if remote_child_file == file_cmp:
                        ffind_flag = 1
                        md5_local = self.localmd5file(local_child_file)
                        if DEBUG_PRINT:
                            self.logger.info('file_remote: %s, md5_remote: %s'%(file_cmp, md5_remote))
                            self.logger.info('file_local: %s, md5_local: %s'%(remote_child_file, md5_local))
                        if md5_local != md5_remote:
                            retscp = self.sshclass.scpwithremote(local_child_file,root_remote)
                            self.logger.info('scp %s to %s'%(local_child_file, root_remote))
                            if retscp == 0:
                                fileupdatecnt += 1
                                filelst.remove(file_remote)
                            else:
                                self.logger.error("scp update file error, ret code: %d"%(retscp))
                                #return retscp
                        else:
                            filelst.remove(file_remote)
                # if not find in filelst, scp local file to it
                if ffind_flag == 0:
                    retscp = self.sshclass.scpwithremote(local_child_file,root_remote)
                    if retscp == 0:
                        filecopycnt += 1
                    else:
                        self.logger.error("scp copy file error, ret code: %d"%(retscp))
                        #return retscp
        if len(pathlst) != 0:
            if DEBUG_PRINT:
                print 'pathlst'
                print pathlst
            self.logger.info("****************Pathlist****************")
            for path_remote in pathlst:
                path_cmp = path_remote.replace('\n','')
                self.sshclass.sshdelfile(path_cmp)
                self.logger.info('remove remote path \'%s\''%(path_cmp))
                filedelcnt += 1
            self.logger.info("****************************************")
        if len(filelst) != 0:
            if DEBUG_PRINT:
                print 'filelst'
                print filelst
            self.logger.info("****************Filelist****************")
            for file_remote in filelst:
                file_cmp = file_remote.split(':')[0]
                print file_cmp
                self.sshclass.sshdelfile(file_cmp)
                self.logger.info('remove remote file \'%s\''%(file_cmp))
                filedelcnt += 1
            self.logger.info("****************************************")
        self.logger.info('Update done!')
        self.logger.info('dircopycnt: %d, filecopycnt: %d, fileupdatecnt: %d, filedelcnt: %d'%(dircopycnt, filecopycnt, fileupdatecnt, filedelcnt))
                    
        fd1.close()
        fd2.close()
        return rc

    '''
    # compare contents of local with remote
    # return code(rc)
        0 --- success
        non-zero --- failure
    '''
    def pathwalkcheck(self):
        rc = 0
        global DEBUG_PRINT
        global MD5FILELOG
        global MD5PATHLOG
        dirdiffcnt = 0  # count of diffrent dirs
        filediffcnt = 0  # count of diffrent files
        fd1 = open(MD5PATHLOG, 'r')
        pathlst = fd1.readlines()
        if DEBUG_PRINT:
            print pathlst
        fd2 = open(MD5FILELOG, 'r')
        filelst = fd2.readlines()
        if DEBUG_PRINT:
            print filelst
        self.logger.info('Start to Checking...')
        listdir_local = os.walk(self.localpath)
        print self.localpath
        print self.remotepath

        for root_local, dir_local, file_local in listdir_local:
            for dirname in dir_local:
                pfind_flag = 0    # find path flag
                local_child_dir = os.path.join(root_local, dirname)
                remote_child_dir = local_child_dir.replace(self.localpath,self.remotepath,1)
                for path_remote in pathlst:
                    # unicode translate
                    upath_remote = unicode(path_remote, 'utf-8')
                    path_cmp = upath_remote.replace('\n','')
                    if remote_child_dir == path_cmp:
                        pathlst.remove(path_remote)
                        pfind_flag = 1
                        pass
    
                # increase the count if not find in remotepathlst file
                if pfind_flag == 0:
                    dirdiffcnt += 1  # increase count of diff dirs
                    
            for filename in file_local:
                ffind_flag = 0    # file find flag
                local_child_file = os.path.join(root_local, filename)
                remote_child_file = local_child_file.replace(self.localpath,self.remotepath,1)
                root_remote = root_local.replace(self.localpath,self.remotepath,1)
                for file_remote in filelst:
                    # unicode translate
                    ufile_remote = unicode(file_remote, 'utf-8')
                    file_cmp = ufile_remote.split(':')[0]
                    md5_remote = file_remote.split(':')[1]
                    md5_remote = md5_remote.split('\n')[0]
                    # if find in the filelst, md5 it and compare with the local file
                    if remote_child_file == file_cmp:
                        ffind_flag = 1
                        md5_local = self.localmd5file(local_child_file)
                        if DEBUG_PRINT:
                            self.logger.info('file_remote: %s, md5_remote: %s'%(file_cmp, md5_remote))
                            self.logger.info('file_local: %s, md5_local: %s'%(remote_child_file, md5_local))
                        if md5_local != md5_remote:
                            self.logger.info('local file:%s, md5:%s not equal with remote file:%s, md5:%s'%(local_child_file, md5_local, remote_child_file, md5_remote))
                            filediffcnt += 1
                        filelst.remove(file_remote)
                # if not find in filelst, scp local file to it
                if ffind_flag == 0:
                    if DEBUG_PRINT:
                        self.logger.info('file_remote: %s, file_local %s'%(remote_child_file, local_child_file))
                    filediffcnt += 1
        if len(pathlst) != 0:
            if DEBUG_PRINT:
                print pathlst
            dirdiffcnt += 1
        if len(filelst) != 0:
            if DEBUG_PRINT:
                print '-'*150
                print 'Diffrent files:'
                print filelst
                print '-'*150
            filediffcnt += 1
        self.logger.info('Check done!')
        self.logger.info('dirdiffcnt: %d, filediffcnt: %d'%(dirdiffcnt, filediffcnt))
                    
        fd1.close()
        fd2.close()
        rc = filediffcnt + dirdiffcnt
        return rc

def Main_thread():
    # the default path
    global MD5FILELOG
    global MD5PATHLOG
    check_cnt = 1
    updateclass = fileupdate('./config/conf.ini')
    updateclass.confparser()
    updateclass.setup_logging()
    updateclass.confinfotolog()
    rc = updateclass.sshwithremote()
    if rc != 0:
        return rc
    rc = updateclass.remotemd5filegenerate()
    if rc != 0:
        return rc
    rc = updateclass.pathwalkcheck()
    count = 0
    while rc != 0 and count < 5:
        updateclass.pathwalkupdate()
        updateclass.remotemd5filegenerate()
        rc = updateclass.pathwalkcheck()
        count += 1
        updateclass.logger.info("Update time count: %d!"%(count))
    endtm = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))
    updateclass.logger.info("-"*100)
    updateclass.logger.info("end time: %s"%(endtm))
    updateclass.logger.info('****************  Update local to remote End  *******************')
    updateclass.logger.info("="*100)
    return 0

def main(argv=None):
    while True:
        Main_thread()
        time.sleep(600)

if __name__ == '__main__':
    main()

