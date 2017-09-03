import sys
import requests
import bs4
import re
if not sys.platform == 'cygwin':
    # pysam doesn't work with cygwin
    import pysam


def main(location, hg_version='hg19', genome=None, upstream=None, downstream=None):
    ''' Return a DNA sequence from a given genomic position or range. 

    Args:
        location: genomic position ('1:10000') or genomic range ('1:10000-10100')
        hg_version: human genome version
        genome: path to genome FASTA file
        upstream: bases upstream from location
        downstream: bases downstream from location
    
    Returns:
        DNA sequence representative of the given genomic
        location or range

    Notes:
        if the location variable is a position then the
        upstream and downstream variables are required to 
        return a sequence. 
    '''
    # correct the hg version
    hg = {'grch37': 'hg19', 'grch38': 'hg38'}
    hg_version = hg.get(hg_version.lower())

    # create a sequence range if required
    seq_range = create_region(location, upstream, downstream)

    # scrape sequence from UCSC or from FASTA file
    if genome:
        seq = get_sequence_locally(seq_range, genome)
    else:
        seq = get_sequence(seq_range, hg_version)

    # capatilise location base if it is a position
    if '-' not in location:
        seq = upper_pos(seq, upstream, downstream)

    return seq


def create_region(location, upstream, downstream):
    ''' Create a genomic range which begins and ends from 
        number of bases upstream and downstream from the
        given genomic location.
    '''
    # PySam doesnt like chr preceding position/range
    location = location.replace('chr', '')

   # check location variable isn't holding a seq range
    if all(x in location for x in [':', '-']):
        return location.replace('-',',')

    chrom, pos = location.split(':')
    start_pos = int(pos) - upstream
    end_pos = int(pos) + downstream
    seq_range = chrom+":"+str(start_pos)+","+str(end_pos)
    return seq_range


def get_sequence(seq_range, hg_version):
    ''' From a genomic range and human genome version, use UCSC DAS server
        to retrieve the sequence found in the given genomic range.

        http://www.biodas.org/documents/spec-1.53.html
    '''
    # scrape for the sequence associated with the seq_range AKA genomic region 
    req = requests.get("http://genome.ucsc.edu/cgi-bin/das/"+hg_version+
                       "/dna?segment="+seq_range.replace('-', ','))
    req.raise_for_status()
    url = bs4.BeautifulSoup(req.text, features="xml").prettify()
    search = re.findall(r"[tacg{5}].*",url)
    
    # filters for elements which only contain nucleotides and concatenate
    seqs = [s for s in search if not s.strip("tacg")] 
    seq = "".join(seqs)
    if not seq:
        error_msg = 'No sequence was found to be associated with {}'.format(seq_range)
        raise IOError(error_msg)
    
    return seq


def get_sequence_locally(seq_range, genome_path):
    ''' Get the DNA sequence of the given genomic range from 
        a locally stored genome FASTA file.
    '''
    # get the sequence associated with a given genomic range from a given fasta file
    chrom, start, end = tuple(re.split(r"[:,]", seq_range))
    chrom = "".join(("chr",chrom))
    genome = pysam.FastaFile(genome_path)

    # -1 is required otherwise the first base is missing, no idea why
    seq = genome.fetch(chrom, int(start)-1, int(end))

    return seq
 

def upper_pos(seq, upstream, downstream):
    ''' Capatilise the position of interest in the sequence.
    '''
    # split up scrapped sequence and make var upper
    before = seq[:upstream]
    var = seq[upstream]
    after = seq[upstream+1:len(seq)]
    altered_seq = "".join((before.lower(), var.upper(), after.lower()))
    return altered_seq 


if __name__ == '__main__':
    print(main('chr15:48408306','hg19',None, 5, 5))