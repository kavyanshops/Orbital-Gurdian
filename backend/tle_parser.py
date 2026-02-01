"""
TLE Parser Module

Parses Two-Line Element (TLE) data into SGP4 satellite objects.
TLE format is the standard for representing orbital elements of Earth-orbiting objects.
"""

from sgp4.api import Satrec, WGS72


def parse_tle(name: str, line1: str, line2: str) -> dict:
    """
    Parse a single TLE into an SGP4 satellite object.
    
    Args:
        name: Satellite/debris name (line 0 of TLE)
        line1: First line of TLE
        line2: Second line of TLE
    
    Returns:
        Dictionary containing:
        - name: Object name
        - satellite: SGP4 Satrec object for propagation
        - catalog_number: NORAD catalog number
    
    Raises:
        ValueError: If TLE format is invalid
    """
    # Validate TLE format
    line1 = line1.strip()
    line2 = line2.strip()
    
    if len(line1) != 69 or len(line2) != 69:
        raise ValueError(f"Invalid TLE line length. Line1: {len(line1)}, Line2: {len(line2)}")
    
    if line1[0] != '1' or line2[0] != '2':
        raise ValueError("TLE lines must start with '1' and '2' respectively")
    
    # Parse using SGP4 library
    satellite = Satrec.twoline2rv(line1, line2, WGS72)
    
    # Extract catalog number from line 1 (columns 3-7)
    catalog_number = line1[2:7].strip()
    
    return {
        'name': name.strip(),
        'satellite': satellite,
        'catalog_number': catalog_number
    }


def parse_tle_batch(tle_text: str) -> list:
    """
    Parse multiple TLEs from a text block.
    
    Expected format:
    NAME 1
    1 XXXXX...
    2 XXXXX...
    NAME 2
    1 XXXXX...
    2 XXXXX...
    
    Args:
        tle_text: Multi-line string containing TLE data
    
    Returns:
        List of parsed TLE dictionaries
    """
    lines = [line.strip() for line in tle_text.strip().split('\n') if line.strip()]
    
    if len(lines) % 3 != 0:
        raise ValueError(f"TLE text must have lines in groups of 3. Got {len(lines)} lines.")
    
    results = []
    for i in range(0, len(lines), 3):
        name = lines[i]
        line1 = lines[i + 1]
        line2 = lines[i + 2]
        
        try:
            parsed = parse_tle(name, line1, line2)
            results.append(parsed)
        except ValueError as e:
            raise ValueError(f"Error parsing TLE for '{name}': {e}")
    
    return results


def validate_tle(line1: str, line2: str) -> bool:
    """
    Validate TLE checksum.
    
    Each TLE line ends with a modulo-10 checksum.
    
    Args:
        line1: First line of TLE
        line2: Second line of TLE
    
    Returns:
        True if checksums are valid
    """
    def compute_checksum(line: str) -> int:
        checksum = 0
        for char in line[:-1]:  # Exclude the checksum digit itself
            if char.isdigit():
                checksum += int(char)
            elif char == '-':
                checksum += 1
        return checksum % 10
    
    line1 = line1.strip()
    line2 = line2.strip()
    
    expected1 = int(line1[-1])
    expected2 = int(line2[-1])
    
    computed1 = compute_checksum(line1)
    computed2 = compute_checksum(line2)
    
    return computed1 == expected1 and computed2 == expected2
