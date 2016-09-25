#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import argparse
import os
import commands

MD5FILELOG = '/tmp/md5checkfilelst.txt'
MD5PATHLOG = '/tmp/md5checkpathlst.txt'
CHECKPATH = '/home/share/CANDANCE/LIBIRARY/work/ZSHX_database'

'''
# create remote file to log md5 check info of all files
# param:
    path_remote --- path to imply the md5 check
    pathlistnam --- log to record path list
    md5filename --- log to record name of md5 check file list
# return code(rc)
    0 --- success
    non-zero --- failure
'''
def md5listofpathwalk(path_remote, pathlistname, md5filename):
    rc = 0
    if os.path.exists(pathlistname):
        rmcmd = 'rm -rf %s'%(pathlistname)
        sta, out = commands.getstatusoutput(rmcmd)
        if sta != 0:
            print "failure: Remove remote md5 path-recording file error!"
            rc = -1
            return rc
    fd_path = open(pathlistname, 'w')
    if fd_path == -1:
        print "failure: Create remote path-recording file error!"
        rc = -2
        return rc
    if os.path.exists(md5filename):
        rmcmd = 'rm -f %s'%(md5filename)
        sta, out = commands.getstatusoutput(rmcmd)
        if sta != 0:
            print "failure: Remove remote md5 file error!"
            rc = -1
            return rc
    fd_file = open(md5filename, 'w')
    if fd_path == -1:
        print "failure: Create remote file error!"
        rc = -2
        return rc
    listdir_remote = os.walk(path_remote)
    for root_remote, dir_remote, file_remote in listdir_remote:
        for dirname in dir_remote:
            remote_child_dir = os.path.join(root_remote, dirname)
            remote_child_dir += '\n'
            fd_path.write(remote_child_dir)
        for filename in file_remote:
            remote_child_file = os.path.join(root_remote, filename)
            md5cmd = 'md5sum \'%s\''%(remote_child_file)
            sta, out = commands.getstatusoutput(md5cmd)
            if sta == 0:
                md5result = out.split(' ')[0]
            else:
                print remote_child_file
                print "failure: %s"%(out)
                rc = -3
                return rc
            md5result = '%s:%s\n'%(remote_child_file,md5result)
            fd_file.write(md5result)
    fd_path.close()
    fd_file.close()
    return rc

def main(argv=None):
    # the default path
    global MD5FILELOG
    global MD5PATHLOG
    global CHECKPATH
    parser = argparse.ArgumentParser(description='file update command.')
    parser.add_argument('-f', '--filepath', nargs='?', dest='filepath', help='MD5 check file list file store path.')
    parser.add_argument('-d', '--dirpath', nargs='?', dest='dirpath', help='MD5 check path walk list file store path.')
    parser.add_argument('-c', '--checkpath', nargs='?', dest='checkpath', help='MD5 check path')
    args = parser.parse_args()

    if args.filepath:
        MD5FILELOG = args.filepath
    if args.dirpath:
        MD5PATHLOG = args.dirpath
    if args.checkpath:
        CHECKPATH = args.checkpath
    if not os.path.exists(CHECKPATH):
        os.makedirs(CHECKPATH)
    rc = md5listofpathwalk(CHECKPATH, MD5PATHLOG, MD5FILELOG)
    if rc != 0:
        print "failure: remote path walk failure, error code :%d"%(rc)
    print "remote md5sum check done!"
    return rc

if __name__ == '__main__':
    sys.exit(main())

