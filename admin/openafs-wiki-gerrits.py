#!/usr/bin/python3
#
# List the open gerrits in descending order on wiki.openafs.org.
#

import os
import tempfile
import git_gerrit
from sh.contrib import git
from sh import ErrorReturnCode, ErrorReturnCode_1

WIKI_DIR = os.path.expanduser('~/src/openafs-wiki')
OPENAFS_DIR = os.path.expanduser('~/src/openafs');

def by_number(c):
    return c['_number']

def info(msg):
    print(msg)

def list_gerrits(fh, branch):
    info('listing gerrits for branch ' + branch)
    fh.write('<p>Changes for branch {branch}.</p>'.format(branch=branch))
    fh.write('<table>\n')
    fh.write('<tr><th>number</th><th>subject</th><th>topic</th></tr>\n')
    terms = 'status:open branch:{branch}'.format(branch=branch)
    for change in sorted(git_gerrit.query(terms, repodir=OPENAFS_DIR), key=by_number, reverse=True):
        if change['topic'] == 'no-topic':
            change['topic'] = ''
        fh.write(
            '<tr>'\
            '<td><a href="https://gerrit.openafs.org/#/c/{_number}">{_number}</a></td>'\
            '<td>{subject}</td>'\
            '<td><a href="https://gerrit.openafs.org/#/q/'\
                 'status:open+project:openafs+branch:{branch}+topic:{topic}">{topic}</td>'\
            '</tr>\n'\
            .format(**change))
    fh.write('</table>')

def update_page(filename, branch):
    info('Updating page ' + filename)
    with open(filename, 'w') as fh:
        list_gerrits(fh, branch)
    git.add(filename)

def main():
    with tempfile.TemporaryDirectory() as tmpdir:
        info('Created tmp directory ' + tmpdir)
        os.chdir(tmpdir)
        git.clone(WIKI_DIR, 'openafs-wiki', _fg=True)
        os.chdir('openafs-wiki')
        git.remote('add', 'gerrit', 'ssh://gerrit.openafs.org/openafs-wiki.git')
        git.fetch('gerrit', _fg=True)
        git.reset('gerrit/master', '--hard', _fg=True)
        update_page('devel/GerritsForMaster.mdwn', 'master')
        update_page('devel/GerritsForStable.mdwn', 'openafs-stable-1_8_x')
        update_page('devel/GerritsForOldStable.mdwn', 'openafs-stable-1_6_x')
        try:
            git.commit('-m', 'update gerrit list', _fg=True)
        except ErrorReturnCode_1:
            print('No changes')
        else:
            git.push('gerrit', 'HEAD:refs/heads/master', _fg=True)

if __name__ == '__main__':
    main()
