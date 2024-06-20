import os, requests, pickle, html5lib, re, warnings
from bs4 import BeautifulSoup

warnings.filterwarnings("ignore", category=DeprecationWarning) 

BASE_URL = 'https://pokemondb.net'
SCRAPED_DATA = 'scraped_data.pickle'
OUTPUT_FILE = 'mon_data.h'

def prInfo(str): print("\033[37m{}\033[00m" .format(str))
def prWarn(str): print("\033[91mwarning: {}\033[00m" .format(str))

def scrape_general_page(base_url):
    # scrape main dex page and store as binary to read infocards later
    if not os.path.exists(SCRAPED_DATA):
        result = requests.get(base_url + "/pokedex/national")
        assert result.status_code == 200, print(f'Attempt to retrieve web page failed - result code {result.status_code}')
        with open(SCRAPED_DATA, 'wb') as f:
            pickle.dump(result, f)
    else:
        with open(SCRAPED_DATA, 'rb') as f:
            result = pickle.load(f)
    return result

def get_ev_yield(ev_yield):
    # format ev yield names for c struct
    output = ''
    val = ev_yield.partition(" ")
    if 'Sp. Atk' in val[2]:
        output += 'SpAttack'
    elif 'Sp. Def' in val[2]:
        output += 'SpDefense'
    else:
        output += val[2]
    output += ' = ' + val[0]
    return output

def clean_name(name):
    return name.replace('♂', '_MALE').replace('♀', '_FEMALE').replace('.', '').replace('\'', '').replace(':', '').replace('-', '_').replace('é', 'e').replace('%', '')

def clean_name_string(name):
    return name.replace('♂', '').replace('♀', '')

def clean_data(string):
    return string.replace('—', 'MISSING_INFO')

def parse_infocards(soup):
    # get a list of all infocards
    infocards = soup.find_all("span", class_="infocard-lg-data text-muted")

    output = '/* THIS FILE IS AUTO-GENERATED! DO NOT EDIT! */\n\n'

    with open(OUTPUT_FILE, 'w') as f:
        f.write(output)

    # write infos line by line
    with open(OUTPUT_FILE, 'a') as f:

        # only check "basic" tabs, ignore things like ability tabs
        tab_regex = re.compile('#tab-basic-.*')
        data_regex = re.compile('tab-basic-.*')
        for ic in infocards:
            # request for linked page to get specific stats
            r = requests.get(BASE_URL + ic.find_all('a')[0]['href'])

            # get species name
            name = ic.find('a').get_text().replace(' ', '_')

            if r.status_code == 200:
                # get tabset for species, this holds data for each form and avoids the script trying to pull data from the move tabset
                other_soup = BeautifulSoup(r.content, 'html5lib').find("div", class_="tabset-basics")
                # get form tabs, a tags that hold the names
                form_tabs = other_soup.find_all("a", class_="sv-tabs-tab", href=tab_regex)
                # get form data sets
                form_data = other_soup.find_all("div", class_="sv-tabs-panel", id=data_regex)

                # iterate through tabs and forms concurrently
                for tab, data in zip(form_tabs, form_data):

                    # this is full of hideous band-aids but its not like pokemon names are gonna change so ¯\_(ツ)_/¯
                    form_name = tab.text.replace(' ', '_')
                    if form_name != name:
                        form_name = clean_name(name + '_' + form_name.replace(name, '').lstrip('_').rstrip('_')).upper().replace('__', '_')
                    else:
                        form_name = clean_name(form_name).upper()

                    prInfo('Scraping species info for ' + form_name)

                    output = '#ifndef INFO_' + form_name + '\n'
                    output += '#define INFO_' + form_name + ' \\\n'

                    # strings
                    # use infocard name rather than the name pulled from the iterated tab
                    output += '.name = COMPOUND_STRING("' + clean_name_string(name).replace('_', ' ') + '"), \\\n'
                    output += '.genus = COMPOUND_STRING("' + data.find("th", text="Species").next_sibling.next_sibling.string.replace(' Pokémon', '') + '"), \\\n'

                    # info
                    output += '.height = ' + clean_data(data.find("th", text="Height").next_sibling.next_sibling.string.split()[0].replace('.', '').lstrip('0')) + ', \\\n'
                    output += '.weight = ' + clean_data(data.find("th", text="Weight").next_sibling.next_sibling.string.split()[0].replace('.', '').lstrip('0')) + ', \\\n'

                    # typing
                    types = data.find("th", text="Type").next_sibling.next_sibling.find_all("a")
                    if len(types) == 1:
                        output += '.types = {TYPE_' + types[0].text.upper() + ', TYPE_' + types[0].text.upper() + '}, \\\n'
                    else:
                        output += '.types = {TYPE_' + types[0].text.upper() + ', TYPE_' + types[1].text.upper() + '}, \\\n'

                    # base stats
                    output += '.baseHP = ' + data.find("th", text="HP").next_sibling.next_sibling.text + ', \\\n'
                    output += '.baseAttack = ' + data.find("th", text="Attack").next_sibling.next_sibling.text + ', \\\n'
                    output += '.baseDefense = ' + data.find("th", text="Defense").next_sibling.next_sibling.text + ', \\\n'
                    output += '.baseSpAttack = ' + data.find("th", text="Sp. Atk").next_sibling.next_sibling.text + ', \\\n'
                    output += '.baseSpDefense = ' + data.find("th", text="Sp. Def").next_sibling.next_sibling.text + ', \\\n'
                    output += '.baseSpeed = ' + data.find("th", text="Speed").next_sibling.next_sibling.text + ', \\\n'

                    # ev yields
                    ev_yield = data.find("th", text="EV yield").next_sibling.next_sibling.text.replace("\n", "")
                    while True:
                        ev = ev_yield.partition(", ")
                        output += '.evYield_' + get_ev_yield(ev[0]) + ', \\\n'
                        if ev[2] == '':
                            break
                        ev_yield = ev[2]

                    # misc
                    output += '.catchRate = ' + clean_data(data.find("th", text="Catch rate").next_sibling.next_sibling.text.split()[0]) + ', \\\n'
                    output += '.expYield = ' + clean_data(data.find("th", text="Base Exp.").next_sibling.next_sibling.text) + ', \\\n'
                    output += '.friendship = ' + clean_data(data.find("a", text="Friendship").find_next("td").text.split()[0]) + ', \\\n'
                    output += '.growthRate = GROWTH_' + clean_data(data.find("th", text="Growth Rate").next_sibling.next_sibling.text.upper().replace(' ', '_')) + ', \\\n'

                    # gender
                    gender = data.find("th", text="Gender").next_sibling.next_sibling.text
                    if gender == 'Genderless':
                        output += '.genderRatio = MON_GENDERLESS, \\\n'
                    else:
                        percent = gender.partition(", ")[2].partition("%")[0]
                        if percent == '0':
                            output += '.genderRatio = MON_MALE, \\\n'
                        elif percent == '100':
                            output += '.genderRatio = MON_FEMALE, \\\n'
                        else:
                            output += '.genderRatio = PERCENT_FEMALE(' + percent + '), \\\n'

                    # egg
                    egg_groups = data.find("th", text="Egg Groups").next_sibling.next_sibling.find_all("a")
                    if len(egg_groups) == 1:
                        output += '.eggGroups = {EGG_GROUP_' + egg_groups[0].text.upper().replace(' ', '_').replace('-', '_') + ', EGG_GROUP_' + egg_groups[0].text.upper().replace(' ', '_').replace('-', '_') + '}, \\\n'
                    elif len(egg_groups) == 2:
                        output += '.eggGroups = {EGG_GROUP_' + egg_groups[0].text.upper().replace(' ', '_').replace('-', '_') + ', EGG_GROUP_' + egg_groups[1].text.upper().replace(' ', '_').replace('-', '_') + '}, \\\n'
                    output += '.eggCycles = ' + clean_data(data.find("a", text="Egg cycles").find_next("td").text.split()[0]) + ', \\\n'

                    # abilities
                    output += '.abilities = { \\\n'
                    abilities = data.find("th", text="Abilities").next_sibling.next_sibling
                    i = 0
                    for ability in abilities.find_all("span"):
                        output += '    [' + str(i) + '] = ABILITY_' + ability.find("a").text.upper().replace(' ', '_').replace('-', '_').replace('\'', '') + ', \\\n'
                        i += 1
                    hidden_ability = abilities.find("small")
                    if hidden_ability != None:
                        output += '    [2] = ABILITY_' + hidden_ability.find("a").text.upper().replace(' ', '_').replace('-', '_').replace('\'', '') + ', \\\n'
                    output += '}\n'

                    # term/write
                    output += '#endif\n\n'
                    f.writelines(output)

def main():
    result = scrape_general_page(BASE_URL)
    soup = BeautifulSoup(result.content, 'html5lib')
    parse_infocards(soup)

if __name__ == "__main__":
    main()
