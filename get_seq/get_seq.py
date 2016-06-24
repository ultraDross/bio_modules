from __future__ import division, print_function
import os, sys,re, click, requests, bs4
from useful_tools.transcription_translation import transcription, translation
from useful_tools.output import write_to_output

class WrongHGversion(Exception):
    pass

class TypographyError(Exception):
    pass
    
class ErrorUCSC(Exception):
    pass

   
@click.command('get_seq')
@click.argument('input_file',nargs=1, required=False)
@click.option('--output_file',default=None, help='give an output file, requires input to be a file')
@click.option('--upstream', default=20, help="number of bases to get upstream, default: 20") # default to an int makes option accept int only
@click.option('--downstream',default=20, help="number of bases to get downstream, default: 20")
@click.option('--hg_version',default="hg19", help="human genome version. default: hg19")
@click.option('--dash/--no_dash',default='n', help="dashes flanking the variant position base. default: --no_dash") # the slash in the option makes it a boolean
@click.option('--header/--no_header',default='n',help="header gives metadata i.e. sequence name etc.")
@click.option('--transcribe/--nr',default='n',help="transcribe into RNA sequence")
@click.option('--translate/--np',default='n',help="translate RNA seq into protein seq")
@click.option('--rc/--no_rc',default='n',help="reverse complement the DNA")
@click.option('--seq_file', default=None, help="match sequence with .seq file contents")

# what use is there in just transcribing and translating for the sake of it? perhaps use an intiation codon finder which can be used o run through a DNA sequence pior to transcripion and transcribing from said site. Also something which checks the dna seq is a multiple of 3 would also be useful. Perhaps something where I could push the rna/protein seq to find which gene exon etc. is or maybe nBLAST, pBLAST etc which I am sure BioPython will have something for parsing to.

def get_seq(input_file, output_file=None, upstream=20, downstream=20, hg_version="hg19"
            , dash="n", header="n", transcribe="n", translate="n",
            rc='n', seq_file=None):
        '''

    Produce a sequence using the UCSC DAS server from an inputted genomic 
	postion and defined number of bases upstream and downstream from said 
	position. A genomic range can be used in place of a genomic position
	and renders the upstream/downstream options irrelevant. An input file
	can have a mixture of genomic positions and genomic ranges.
         \b\n
    A file or string can be used as input. STRING: either a variant position 
    or a genomic range deliminated by a comma. FILE: deliminated file with 
    the variant name and the variant position
         \b\n
    Example:\b\n
        get_seq chr1:169314424 --dash --upstream 200 --downstream 200\n
        get_seq chr1:169314424,169314600 --hg_version hg38\n
        get_seq input.txt --output_file output.txt --header\n
        ''' 
        # allows one to pipe in an argument at the cmd, requires required=False in 
        # @click.argument()
        if not input_file:
            input_file = input()
        
        # parse all arguments into the Processing Class 
        process = Processing(input_file,output_file,upstream,downstream,hg_version
                             ,dash,transcribe,translate,rc,header, seq_file)
        
        # if the arg given is a file, parse it in line by line
        if os.path.isfile(input_file) is True:

            for line in [line.rstrip("\n").split("\t") for line in open(input_file)]:
                seq_name = line[0]
                var_pos = line[1]
                sequence = temp(seq_name, var_pos, process)

        else:
            temp("query", input_file, process)




        

def temp(seq_name, var_pos, process):
        # adds all scrapped data to a list, which is written to an output file if the 
        # option is selected
        try:
            # check each individual line of the file for CUSTOM ERRORS
            error_check = process.handle_argument_exception(var_pos)
            
            # check if var_pos is a GENOMIC REGION, else construct one from var_pos
            seq_range = process.create_region(var_pos)
            
            # use UCSC to get the genomic ranges DNA sequence
            sequence = process.get_region_info(seq_range)
            
            # assess whether the var pos base in the sanger trace (seq_file) is different to the reference base 
            sanger_sequence = process.match_with_seq_file(sequence)
            ref_base = sanger_sequence[1]
            sanger_base = sanger_sequence[2]

            # compare the reqerence var_pos base and the sanger var_pos base
            compare = process.compare_nucleotides(ref_base,sanger_base)
            
            
            # detrmine whether to transcribe or translate to RNA or PROTEIN
            sequence = process.get_rna_seq(sequence)
            sequence = process.get_protein_seq(sequence)

            # determine whether to give a HEADER
            header = process.header_option(seq_name,var_pos,
                                           seq_range,sequence)
            
            print("\n".join((header,"Reference Sequence:\t"+sequence,"Sanger Sequence:\t"+sanger_sequence[0],compare)))
            
            #return seq_name,var_pos,seq_range,sequence,sanger_sequence

        except WrongHGversion:
            print("Human genome version "+hg_version+" not recognised")
            sys.exit(0)
        except TypographyError:
            print("Only one colon and no more than one comma/dash is allowed for "
                  +var_pos+" in "+seq_name+"\n")    
        except ErrorUCSC:
            print(var_pos+" in "+seq_name+" is not recognised by UCSC"+"\n")
      
        






class Processing():

    def __init__(self,input_file,output_file,upstream, downstream, hg_version, 
                 dash, transcribe, translate,rc,header,seq_file):
        
        self.input_file = input_file
        self.output_file = output_file
        self.upstream = upstream
        self.downstream = downstream
        self.hg_version = hg_version
        self.dash = dash
        self.transcribe = transcribe
        self.translate = translate
        self.rc = rc
        self.header = header
        self.seq_file = seq_file

    UIPAC = {"A":"A", "C":"C", "G":"G", "T":"T",
             "R":"A/G", "Y":"C/T", "S":"G/C",
             "W":"A/T", "K":"G/T", "M":"A/C",
             "B":"C/G/T", "D":"A/G/T", "H":"A/C/T",
             "V":"A/C/G", "N":"N"}

              
    def handle_argument_exception(self,var_pos):
        ''' Stores custom exceptions
        '''        
        
        if self.hg_version not in ["hg16","hg17","hg18","hg19","hg38"]:
            raise WrongHGversion("Human genome version "+self.hg_version+
                                 " not recognised")
            sys.exit(0)
            
        
        if var_pos.count(",") > 1 or var_pos.count("-") >1:
            raise TypographyError("too many commas in "+self.input_file)
            
            
        if var_pos.count(":") < 1 or var_pos.count(":") >1:
            raise TypographyError("A single colon is required to seperate"+\
                                  "the chromosome and position numbers in the"+\
                                  "variant position: "+self.input_file)
                                             
                
    def create_region(self,var_pos):
        ''' use the variant position given, add and subtract the 
            numbers given in upstream and downstream respectively
            from the given variant position to return a genomic range.
        '''
        # check if var_pos is a GENOMIC REGION, else construct one from var_pos
        if re.search(r"[,-]",var_pos):
            var_pos = var_pos.replace("-",",")
            return var_pos

        else:                    
            nospace = var_pos.replace(" ","")
            chrom = nospace.split(":")[0]
            pos = nospace.split(":")[1]
            start_pos = int(pos) - self.upstream
            end_pos = int(pos) + self.downstream
            seq_range = chrom+":"+str(start_pos)+","+str(end_pos)
            return seq_range
                
                
    def get_region_info(self, seq_range):
        ''' From a genomic range and human genome version, use UCSC DAS server
            to retrieve the sequence found in the given genomic range.
        '''
        # scrape for the sequence associated with the seq_range AKA genomic region 
        req = requests.get("http://genome.ucsc.edu/cgi-bin/das/"+self.hg_version+
                               "/dna?segment="+seq_range)
        req.raise_for_status()
        url = bs4.BeautifulSoup(req.text, features="xml").prettify()
        search = re.findall(r"[tacg{5}].*",url)
        
        # filters for elements which only contain nucleotides and concatenate
        seqs = [s for s in search if not s.strip("tacg")] 
        seq = "".join(seqs)
        if not seq:
            raise ErrorUCSC
        
        
        # flank the base associated with the variant position with dashes
        if self.dash:
            downstream = seq[:self.upstream]
            var = seq[self.upstream]
            upstream = seq[self.upstream+1:len(seq)]
            answer = "".join((downstream,"-",var,"-",upstream))
            return answer
    
        # return sequence without dashes
        if not self.dash:
            return seq


    def get_rna_seq(self,sequence):
        ''' determine whether to transcribe rna,
            based upon options selected
        '''
        # perorm transcription, reverse complement and/or translation depending
        # on which options have been selected
        if self.transcribe:
         
            if self.rc:
                rna = transcription(sequence.replace("-",""),"rc")
                return rna

            else:
                rna = transcription(sequence.replace("-",""))
                return rna
        else:
            # DNA
            return sequence


        
    def get_protein_seq(self,rna):
        ''' determine whether to translate protein,
            based upon options selected
        '''
        if self.translate:
            protein = translation(rna)
            return protein
        else:
            return rna
   


    def match_with_seq_file(self,sequence):
        ''' search for the sequence output from 
            get_region_info() in a given 
            .seq file and output it

            returns a tuple containing the sanger
            sequence and the var_pos nucelotide

            # NEEDS MUCH MORE TESTING
        '''
        if self.seq_file:
            # get the sequence preceding the var_pos (preseq) and the var_pos sequence (ref_seq) 
            # from the returned get_region_info() value 
            preseq = sequence[:self.upstream].upper()
            ref_seq = sequence[self.upstream+1].upper()
            seq_file = open(self.seq_file, "r").read()
            seq_file = seq_file.replace("\n","")
            
            # find the preseq in the seq_file string and output the indexes where the match occurred within the 
            # seq_file as a tuple
            find = [(m.start(0), m.end(0)) for m in re.finditer(preseq, seq_file)][0]
            start = find[0]
            end = find[1]
            
            # get the full sequence of interest from the seq_file
            matched_seq = seq_file[start:end]
            var_pos_seq = Processing.UIPAC.get(seq_file[end])  # convert the UIPAC to bases
            downstream_seq = seq_file[end+1:end+self.downstream+1]
            if self.dash:
                full_seq = "-".join((matched_seq,var_pos_seq,downstream_seq))
            else:
                full_seq = "".join((matched_seq,var_pos_seq,downstream_seq))


            return(full_seq,ref_seq,var_pos_seq.upper())
            


    def compare_nucleotides(self,base_1, base_2):
            '''compare two nucleotides
            '''
            
            # assess whether a variant is present in the sanger sequence in the given proposed variant position
            if base_1 != base_2:
                #print(".seq file:\t"+full_seq)
                return("the nucleotides given are DIFFERENT")

            elif base_1== base_2:
                #print(".seq file:\t"+full_seq)
                return("the nucleotides given are the SAME")
            
            else:
                return "not found"


    
    def header_option(self,seq_name,var_pos,seq_range,sequence):
        ''' determine whether to place a header
            above the returned sequence, based 
            upon options selected by user
        '''
        # concatenate the name and outputs from Class, determine whether to 
        # add a header
        if self.header:
            header = " ".join((">",seq_name,var_pos,seq_range))
        else:
            header = ""

        # output sequences to the screen and append to a list
        return(header)

         
                
if __name__ == '__main__':
    get_seq()         

# get_seq("in.txt","b", 2, 20,"hg19","\t","y")

