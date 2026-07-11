"""Log export helpers."""

import logging


logger = logging.getLogger("__name__")


def get_bands(database):
    """Return a list of bands worked, and an empty list if none worked."""
    bandlist = []
    list_o_bands = database.get_bands()
    if list_o_bands:
        for count in list_o_bands:
            bandlist.append(count[0])
        return bandlist
    return []


def generate_band_mode_tally(database, bands, filename="Statistics.txt"):
    """Generate band/mode tally."""
    blist = get_bands(database)
    with open(filename, "w", encoding="utf-8") as file_descriptor:
        print("\t\tCW\tPWR\tDI\tPWR\tPH\tPWR", end="\r\n", file=file_descriptor)
        print("-" * 60, end="\r\n", file=file_descriptor)
        for band in bands:
            if band in blist:
                cwt = database.get_band_mode_tally(band, "CW")
                dit = database.get_band_mode_tally(band, "DI")
                pht = database.get_band_mode_tally(band, "PH")
                print(
                    f"Band:\t{band}\t{cwt[0]}\t{cwt[1]}\t{dit[0]}"
                    f"\t{dit[1]}\t{pht[0]}\t{pht[1]}",
                    end="\r\n",
                    file=file_descriptor,
                )
                print("-" * 60, end="\r\n", file=file_descriptor)


def get_state(section, sec_state):
    """Return the US state a section is in, or Bool False if none was found."""
    try:
        state = sec_state[section]
        if state != "--":
            return state
    except IndexError:
        return False
    except KeyError:
        return False
    return False


def fakefreq(fakefreqs, band, mode):
    """
    Return a sane frequency in khz if unable to obtain a frequency from the rig.
    """
    logger.info("fakefreq: band:%s mode:%s", band, mode)
    modes = {"CW": 0, "DI": 1, "PH": 2, "FT8": 1, "SSB": 2}
    if not band:
        return 0
    freqtoreturn = fakefreqs[band][modes[mode]]
    logger.info("fakefreq: returning:%s", freqtoreturn)
    return freqtoreturn


def write_adif(
    database,
    preference,
    sec_state,
    fakefreqs,
    filename="FieldDay.adi",
):
    """Create an ADIF file of the contacts made."""
    log = database.fetch_all_contacts_asc()
    if not log:
        return False
    with open(filename, "w", encoding="ascii") as file_descriptor:
        print("<ADIF_VER:5>2.2.0", end="\r\n", file=file_descriptor)
        print("<EOH>", end="\r\n", file=file_descriptor)
        for contact in log:
            (
                _,
                hiscall,
                hisclass,
                hissection,
                the_datetime,
                freq,
                band,
                mode,
                _,
                grid,
                opname,
                _,
                _,
            ) = contact
            if mode == "DI":
                mode = "FT8"
            if mode == "PH":
                mode = "SSB"
            if mode == "CW":
                rst = "599"
            else:
                rst = "59"
            loggeddate = the_datetime[:10]
            loggedtime = the_datetime[11:13] + the_datetime[14:16]
            try:
                temp = str(freq / 1000000).split(".")
                freq = temp[0] + "." + temp[1].ljust(3, "0")
            except TypeError:
                freq = "UNKNOWN"

            if freq == "0.000":
                freq = int(fakefreq(fakefreqs, band, mode))
                temp = str(freq / 1000).split(".")
                freq = temp[0] + "." + temp[1].ljust(3, "0")

            print(
                f"<QSO_DATE:{len(''.join(loggeddate.split('-')))}:d>"
                f"{''.join(loggeddate.split('-'))}",
                end="\r\n",
                file=file_descriptor,
            )
            print(
                f"<TIME_ON:{len(loggedtime)}>{loggedtime}",
                end="\r\n",
                file=file_descriptor,
            )
            print(f"<CALL:{len(hiscall)}>{hiscall}", end="\r\n", file=file_descriptor)
            print(f"<MODE:{len(mode)}>{mode}", end="\r\n", file=file_descriptor)
            print(
                f"<BAND:{len(band + 'M')}>{band + 'M'}",
                end="\r\n",
                file=file_descriptor,
            )
            print(f"<FREQ:{len(freq)}>{freq}", end="\r\n", file=file_descriptor)
            print(f"<RST_SENT:{len(rst)}>{rst}", end="\r\n", file=file_descriptor)
            print(f"<RST_RCVD:{len(rst)}>{rst}", end="\r\n", file=file_descriptor)
            print(
                "<STX_STRING:"
                f"{len(preference['myclass'] + ' ' + preference['mysection'])}>"
                f"{preference['myclass'] + ' ' + preference['mysection']}",
                end="\r\n",
                file=file_descriptor,
            )
            print(
                f"<SRX_STRING:{len(hisclass + ' ' + hissection)}>"
                f"{hisclass + ' ' + hissection}",
                end="\r\n",
                file=file_descriptor,
            )
            print(
                f"<ARRL_SECT:{len(hissection)}>{hissection}",
                end="\r\n",
                file=file_descriptor,
            )
            print(f"<CLASS:{len(hisclass)}>{hisclass}", end="\r\n", file=file_descriptor)
            state = get_state(hissection, sec_state)
            if state:
                print(f"<STATE:{len(state)}>{state}", end="\r\n", file=file_descriptor)
            if len(grid) > 1:
                print(
                    f"<GRIDSQUARE:{len(grid)}>{grid}",
                    end="\r\n",
                    file=file_descriptor,
                )
            if len(opname) > 1:
                print(f"<NAME:{len(opname)}>{opname}", end="\r\n", file=file_descriptor)
            comment = "ARRL-FD"
            print(f"<COMMENT:{len(comment)}>{comment}", end="\r\n", file=file_descriptor)
            print("<EOR>", end="\r\n", file=file_descriptor)
            print("", end="\r\n", file=file_descriptor)
    return True


def write_cabrillo(
    database,
    preference,
    fakefreqs,
    claimed_score,
    qrp,
    highpower,
    filename=None,
):
    """Generate a Cabrillo log file."""
    log = database.fetch_all_contacts_asc()
    if not log:
        return False
    if filename is None:
        filename = preference["mycall"].upper() + ".log"
    catpower = ""
    if qrp:
        catpower = "QRP"
    elif highpower:
        catpower = "HIGH"
    else:
        catpower = "LOW"
    with open(filename, "w", encoding="ascii") as file_descriptor:
        print("START-OF-LOG: 3.0", end="\r\n", file=file_descriptor)
        print("CREATED-BY: K6GTE Field Day Logger", end="\r\n", file=file_descriptor)
        print("CONTEST: ARRL-FD", end="\r\n", file=file_descriptor)
        print(f"CALLSIGN: {preference['mycall']}", end="\r\n", file=file_descriptor)
        print("LOCATION:", end="\r\n", file=file_descriptor)
        print(
            f"ARRL-SECTION: {preference['mysection']}",
            end="\r\n",
            file=file_descriptor,
        )
        print(f"CATEGORY: {preference['myclass']}", end="\r\n", file=file_descriptor)
        print(f"CATEGORY-POWER: {catpower}", end="\r\n", file=file_descriptor)
        print(f"CLAIMED-SCORE: {claimed_score}", end="\r\n", file=file_descriptor)
        print(f"OPERATORS: {preference['mycall']}", end="\r\n", file=file_descriptor)
        print("NAME: ", end="\r\n", file=file_descriptor)
        print("ADDRESS: ", end="\r\n", file=file_descriptor)
        print("ADDRESS-CITY: ", end="\r\n", file=file_descriptor)
        print("ADDRESS-STATE: ", end="\r\n", file=file_descriptor)
        print("ADDRESS-POSTALCODE: ", end="\r\n", file=file_descriptor)
        print("ADDRESS-COUNTRY: ", end="\r\n", file=file_descriptor)
        print("EMAIL: ", end="\r\n", file=file_descriptor)
        for contact in log:
            (
                _,
                hiscall,
                hisclass,
                hissection,
                the_datetime,
                freq,
                band,
                mode,
                _,
                _,
                _,
                _,
                _,
            ) = contact
            if mode == "DI":
                mode = "DG"
            loggeddate = the_datetime[:10]
            loggedtime = the_datetime[11:13] + the_datetime[14:16]
            try:
                temp = str(freq / 1000000).split(".")
                freq = temp[0] + temp[1].ljust(3, "0")[:3]
            except TypeError:
                freq = "UNKNOWN"
            if freq == "0000":
                freq = fakefreq(fakefreqs, band, mode)
            print(
                f"QSO: {freq.rjust(6)} {mode} {loggeddate} {loggedtime} "
                f"{preference['mycall']} {preference['myclass']} "
                f"{preference['mysection']} {hiscall} {hisclass} {hissection}",
                end="\r\n",
                file=file_descriptor,
            )
        print("END-OF-LOG:", end="\r\n", file=file_descriptor)
    return True
