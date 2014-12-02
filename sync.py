#!/usr/bin/env python
# -*- coding: utf-8 -*-
import urllib2, re, os
import pickle
from time import sleep

#IPAD_IP = '172.20.10.3'
#IPAD_IP = '10.0.0.17'
IPAD_IP = '100.100.100.157'
BASE_PATH = '/Users/puchinger/Desktop/Work/'


def main():
    albums_ipad = get_albums_ipad()
    albums_desktop = get_albums_desktop()
    
    #for i in albums_desktop.keys()[2:]:
    #   del albums_desktop[i]

    
    # create empty albums
    albums_diff = list(set(albums_ipad.keys()) ^ set(albums_desktop.keys()))
    for i in albums_diff:
        if i in albums_ipad:
            create_album_desktop(i)
        else:
            create_album_ipad(i)
    
                
    album_ids = get_albumids()
    if os.path.exists('sync.pickle'):
        sync_status = pickle.load(open('sync.pickle', 'r'))
    else:
        sync_status = {}
    sync_ipad = sync_status.keys()
    sync_desktop = sync_status.values()

    try:
        # NEW: desktop -> ipad
        for album in albums_desktop.keys():
            pics_desktop = albums_desktop[album]
            
            for pic in sorted(pics_desktop.keys()):
                if not os.path.join(BASE_PATH, album, pic) in sync_desktop:
                    #print repr(pic),pic.endswith('ds_store')
                    if pic.endswith('ds_store'):
                        os.remove(os.path.join(BASE_PATH, album, pic))
                    else:
                        pic_id = upload_from_desktop(album_ids[album], pic, pics_desktop[pic])
                        sync_status[pic_id] = pics_desktop[pic]


        # NEW: desktop <- ipad
        for album in albums_ipad.keys():
            pics_ipad = albums_ipad[album]

            for pic in sorted(pics_ipad.keys()):
                x = pics_ipad[pic].find('=')
                pic_id = int(pics_ipad[pic][x+1:])
                    
                if not pic_id in sync_ipad:
                    pic_path = download_from_ipad(i, pic, pics_ipad[pic])
                    sync_status[pic_id] = pic_path

        # todo: deletions!

        pickle.dump(sync_status, open('sync.pickle', 'w'))
    except:
        pickle.dump(sync_status, open('sync.pickle', 'w'))
        raise


def download_from_ipad(album, pic, pic_url):
    print 'ipad -> desktop:', pic_url

    url = 'http://%s:8080%s' % (IPAD_IP, pic_url)
    rq = urllib2.Request(url)
    rs = urllib2.urlopen(rq)
    data = rs.read()
    
    file_path = BASE_PATH + album + os.sep + pic
    f = open(file_path, 'wb')
    f.write(data)
    f.close()

    return pic


def upload_from_desktop(album_id, pic, pic_path):
    print 'ipad <- desktop:', pic_path
    
    data =  '------------ei4GI3gL6Ij5cH2ei4ei4Ef1Ij5GI3\r\n'
    data += 'Content-Disposition: form-data; name="Filename"\r\n'
    data += '\r\n'
    data += '%s\r\n' % pic
    data += '------------ei4GI3gL6Ij5cH2ei4ei4Ef1Ij5GI3\r\n'
    data += 'Content-Disposition: form-data; name="Filedata"; filename="%s"\r\n' % pic
    data += 'Content-Type: application/octet-stream\r\n'
    data += '\r\n'
    
    f = open(pic_path, 'rb')
    data += f.read()
    f.close()
    
    data += '\r\n'
    data += '------------ei4GI3gL6Ij5cH2ei4ei4Ef1Ij5GI3\r\n'
    data += 'Content-Disposition: form-data; name="Upload"\r\n'
    data += '\r\n'
    data += 'Submit Query\r\n'
    data += '------------ei4GI3gL6Ij5cH2ei4ei4Ef1Ij5GI3--'
    
    old_pics = get_album_pics_form_ipad(album_id)

    url = 'http://%s:8080/upload?albumId=%i&fileName=%s' % (IPAD_IP, album_id, urllib2.quote(pic).replace('.', '%2E'))
    rq = urllib2.Request(url, data)
    rq.add_header('Content-Type', 'multipart/form-data; boundary=----------ei4GI3gL6Ij5cH2ei4ei4Ef1Ij5GI3')
    rq.add_header('Origin', 'http://172.20.10.3:8080')
    rq.add_header('Referer', 'http://172.20.10.3:8080/album?id=53')
    rq.add_header('Connection', 'keep-alive')
    rs = urllib2.urlopen(rq)
    rs.read()
    
    diff = []
    
    while len(diff) == 0:
        new_pics = get_album_pics_form_ipad(album_id)
        diff = list(set(old_pics.values()) ^ set(new_pics.values()))
        if len(diff) == 0: sleep(.05)
    
    x = diff[-1].find('=')
    return int(diff[-1][x+1:])


def create_album_desktop(album):
    print 'NEW on desktop:', album
    os.mkdir(BASE_PATH + album)

def create_album_ipad(album):
    print 'NEW on ipad:', album
    url = 'http://%s:8080/create-album?name=%s&parentId=0' % (IPAD_IP, urllib2.quote(album))

    try:
        rq = urllib2.Request(url)
        rs = urllib2.urlopen(rq)
        html = rs.read()
    except:
        rq = urllib2.Request(url)
        rs = urllib2.urlopen(rq)
        html = rs.read()
        sleep(.1)

def get_albums_ipad():
    base_url = 'http://%s:8080' % IPAD_IP

    rq = urllib2.Request(base_url)
    rs = urllib2.urlopen(rq)
    html = rs.read()
    
    ret = {}
    for album_id, name in re.findall('<a class="album-name" href="/album[?]id=(\d+)">(.+)</a>', html):
        if album_id != '0':
            album = get_album_pics_form_ipad(int(album_id))
            
            ret[urllib2.unquote(name)] = album
    return ret

def get_album_pics_form_ipad(album_id):
    base_url = 'http://%s:8080' % IPAD_IP
    path = '/album?id=%i' % album_id
    
    rq = urllib2.Request(base_url + path)
    rs = urllib2.urlopen(rq)
    html = rs.read()
    
    album = {}
    for link in [path, ] + re.findall('<a href="(/album[^"]+)">', html):
        if link != path:
            rq = urllib2.Request(base_url + link)
            rs = urllib2.urlopen(rq)
            html = rs.read()
        
        for pic_path, pic_name in re.findall('<a href="(/media/([^"?]+)[?]id=\d+)">', html):
            pic_name = urllib2.unquote(pic_name).lower()
            if pic_name == ' .jpg':
                pic_name = re.findall('\d+', pic_path)[-1] + '.jpg'
            album[pic_name] = pic_path
    return album

def get_albumids():
    base_url = 'http://%s:8080' % IPAD_IP
    
    rq = urllib2.Request(base_url)
    rs = urllib2.urlopen(rq)
    html = rs.read()

    ret = {}
    for id, name in re.findall('<a class="album-name" href="/album[?]id=(\d+)">(.+)</a>', html):
        if id != '0':
            ret[name] = int(id)
    return ret

def get_albums_desktop():
    ret = {}
    for i in os.listdir(BASE_PATH):
        album_path = BASE_PATH + i
        
        if os.path.isdir(album_path):
            album = {}
            
            for pic in os.listdir(album_path):
                if pic.startswith('.'):
                    pass
                else:
                    album[pic.lower()] = os.sep.join((album_path, pic))
            ret[i] = album
    return ret


if __name__ == '__main__':
    main()