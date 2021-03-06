#!/usr/bin/env python


import requests
import re
import json
import os
from lxml import html


def scrap_page(page):
    properties = []
    r = requests.get(page)
    print('Scraping %s' % page)
    if r.status_code != 200:
        raise Exception('status %s' % r.status_code)
    htmltree = html.fromstring(r.content)
    with open('out.html', 'w') as fh:
        fh.write(html.tostring(htmltree))
    tables = htmltree.xpath('''//div[@class='rst-content']//table''')

    if len(tables) == 0:
        raise Exception('Cannot find documentation table')

    if len(tables) > 1:
        raise Exception('Found too many documentation tables')

    rows = htmltree.xpath('''//div[@class='rst-content']//table/tbody//tr''')
    if len(rows) == 0:
        raise Exception('Could not find documentation table for %s' % page)

    for row in rows:
        entry = {}
        items = row.xpath('''./td''')
        # Skip empty rows
        if items == []:
            #print ("Empty row")
            continue
        entry['name'] = items[0].text_content().strip()
        type_text = items[1].text_content().strip()
        type_text = re.sub('^<', '', type_text)
        type_text = re.sub('>$', '', type_text)

        # Will throw KeyError if type text is not found in dict
        entry['type'] = {
            'String': 'str',
            'Integer': 'int',
            'Boolean': 'bool',
            'Double': 'float',
            'Double[]': 'list',
            'String[]': 'list',
        }[type_text]

        readonly_text = items[2].text_content().strip()
        if readonly_text == 'Read-only':
            entry['readonly'] = True
        elif readonly_text == 'Read-write':
            entry['readonly'] = False
        else:
            raise Exception('Got unexpected value for read only attribute "%s"' % readonly_text)

        # Description
        entry['description_lines'] = items[3].text.strip().split('<br>')

        # Check if we have choices list
        for line in entry['description_lines']:
            if line.startswith('Possible values'):
                choices = []
                values_str = re.sub('Possible values = ', '', line)
                choices = [val.strip() for val in values_str.split(',')]
                entry['choices'] = choices
        properties.append(entry)
    return properties


def update_for_immutables(properties, base_command_url, item):
    m = re.match(r'^.*/(.*)$', item)
    if m is None:
        raise Exception('Cannot match item: ' % item)
    # command_with_dashes = m.group(1)
    command_with_spaces = m.group(1).replace('-', ' ')

    page = base_command_url + item + '/'

    print('Scraping %s' % page)
    r = requests.get(page)
    htmltree = html.fromstring(r.content)
    # id = 'set-%s' % command_with_dashes
    h2s = htmltree.xpath('''//h2/following-sibling::p''')
    for h2 in h2s:
        if h2.text is not None:
            doc_text = h2.text.strip().lower()
            if doc_text.startswith('set %s' % command_with_spaces):
                break
    else:
        raise Exception('Cannot find "set %s"' % command_with_spaces)
    # print(doc_text)
    mutable_options = [item[1:] for item in re.findall(r'-\w+', doc_text)]
    # print('Mutables %s' % mutable_options)
    updated_properties = []
    for property in properties:
        # print('Muting property %s' % property['name'])
        property['mutable'] = property['name'] in mutable_options
        # print('new property %s' % property)
        updated_properties.append(property)
    return updated_properties
    # print('options: %s' % [ item[1:] for item in re.findall(r'-\w+', doc_text)])


def main():
    #base_nitro_url = 'https://docs.citrix.com/en-us/netscaler/11-1/nitro-api/nitro-rest/api-reference/configuration/'
    #base_command_url = 'https://docs.citrix.com/en-us/netscaler/11-1/reference/netscaler-command-reference/'

    base_nitro_url = 'https://developer-docs.citrix.com/projects/netscaler-nitro-api/en/12.0/configuration/'
    base_command_url = 'https://developer-docs.citrix.com/projects/netscaler-command-reference/en/12.0/'
    pages = [
        ('basic/service/service', 'basic/service/service'),
        ('basic/servicegroup/servicegroup', 'basic/servicegroup/servicegroup'),
        ('basic/server/server', 'basic/server/server'),
        ('basic/servicegroup_servicegroupmember_binding/servicegroup_servicegroupmember_binding', None),
        ('load-balancing/lbvserver/lbvserver', 'lb/lb-vserver/lb-vserver'),
        ('load-balancing/lbvserver_service_binding/lbvserver_service_binding', None),
        ('load-balancing/lbvserver_servicegroup_binding/lbvserver_servicegroup_binding', None),
        ('load-balancing/lbmonitor/lbmonitor', 'lb/lb-monitor/lb-monitor'),
        ('content-switching/csvserver/csvserver', 'cs/cs-vserver/cs-vserver'),
        ('content-switching/cspolicy/cspolicy', 'cs/cs-policy/cs-policy'),
        ('content-switching/csaction/csaction', 'cs/cs-action/cs-action'),

        ('ssl/sslcertkey/sslcertkey', 'ssl/ssl-certkey/ssl-certkey'),
        ('ssl/sslvserver_sslcertkey_binding/sslvserver_sslcertkey_binding', None),
        ('global-server-load-balancing/gslbsite/gslbsite', 'gslb/gslb-site/gslb-site'),
        ('global-server-load-balancing/gslbservice/gslbservice', 'gslb/gslb-service/gslb-service'),
        ('global-server-load-balancing/gslbvserver/gslbvserver', 'gslb/gslb-vserver/gslb-vserver'),
        ('global-server-load-balancing/gslbvserver_domain_binding/gslbvserver_domain_binding', None),
    ]
    for page in pages:
        page_file = re.sub('/', '_', page[0])
        page_file = page_file[:page_file.rindex('_')]
        page_file += '.json'
        if os.path.exists(page_file):
            print('Skipping %s' % page_file)
            continue
        properties = scrap_page(base_nitro_url + page[0] + '/')
        if page[1] is not None:
            properties = update_for_immutables(properties, base_command_url, page[1])
        print('writing to file %s' % page_file)
        with open(page_file, 'w') as fh:
            json.dump(properties, fh, indent=4)


if __name__ == '__main__':
    main()
