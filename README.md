# mon-data

A simple python tool for scraping Pokémon data from [pokemondb.net](pokemondb.net) and formatting it for GBA [decompilation projects](https://github.com/pret).

> Note: The outputted data is not compatable with standard decompilation projects (like pokeeemerald) by default. These tools were written for the development of Pokémon Saffron Version, which uses a significantly modified data structure. The way this script writes to the data structure is very simple and can be modified to your needs.

## Scraping the data

To scrape the data for all Pokémon and their subforms, run the following from the root directory.

```zsh
./setup.sh && source .venv/bin/activate && python3 scrape_data.py
```

## Including the outputted data

The scraped data is nested in defines rather than writing directly as a structure. This allows appending data exclusive to your project or entirely overriding data on species by species basis without editing the outputted file. To override the data of a species, write your preffered species data in the same format to a new file (e.g. ```my_override_data.h```), and include that file **before** including ```mon_data.h```.

```c
#include "my_override_data.h"
#include "mon_data.h"

const struct SpeciesInfo gSpeciesInfo[] =
{
    [SPECIES_BULBASAUR] =
    {
        INFO_BULBASAUR,
        .dexNum = NATIONAL_DEX_BULBASAUR,
        .region = NATIVE_KANTO
    },
};
```