# channel_equalizer class 
# Last modification by Marko Kosunen, marko.kosunen@aalto.fi, 05.01.2018 11:07
#Add TheSDK to path. Importing it first adds the rest of the modules
#Simple buffer template
import os
import sys

import numpy as np
import tempfile

from thesdk import *
from verilog import *
from verilog.testbench import *
from verilog.testbench import testbench as vtb

from signal_generator_802_11n import PLPCsyn_long


class channel_equalizer(verilog,thesdk):
    @property
    def _classfile(self):
        return os.path.dirname(os.path.realpath(__file__)) + "/"+__name__

    def __init__(self,*arg): 
        self.proplist = [ 'Rs', 'symbol_length', 'Users' ];    #properties that can be propagated from parent
        self.Rs = 160e6;                   # Sampling frequency
        self.Users = 16;                   # Number of users
        self.symbol_length  = 64;          # OFDM symbol length
        self.A = IO();            # Input data, FFT Bins in series 
        self._Z = IO();           # Output, equalized FFT bins
        self.control_in = IO()
        self.control_in.Data = Bundle()
        self.control_out = IO()
        self.control_out.Data = Bundle()
        self.model='py';             #can be set externally, but is not propagated
        self.par= False              #By default, no parallel processing
        self.queue= []               #By default, no parallel processing

        if len(arg)>=1:
            parent=arg[0]
            self.copy_propval(parent,self.proplist)
            self.parent =parent;
        self.init()
    def init(self):
        #This gets updated every time you add an iofile
        self.iofile_bundle=Bundle()
        #Adds files to bundle
        _=verilog_iofile(self,name='Z',datatype='complex')
        _=verilog_iofile(self,name='A',dir='in')
        self.vlogparameters=dict([ ('g_Rs',self.Rs),])

    def main(self):
        out=np.array(self.A.Data)
        if self.par:
            self.queue.put(out)
        self._Z.Data=out

    def run(self,*arg):
        if len(arg)>0:
            self.par=True      #flag for parallel processing
            self.queue=arg[0]  #multiprocessing.queue as the first argument
        if self.model=='py':
            self.main()
        else: 
          if self.model=='sv':
              if not 'control_file' in self.control_in.Data.Members:
                  self.create_controlfile()
                  self.reset_sequence()
              else:
                  self.control_in.Data.Members['control_file'].adopt(parent=self)

              # Create testbench and execute the simulation
              self.define_testbench()
              self.tb.export(force=True)
              self.write_infile()
              self.run_verilog()
              #self.read_outfile()
              #del self.iofile_bundle

          elif self.model=='vhdl':
              self.print_log(type='F', msg='VHDL model not yet supported')

    def write_infile(self):
        #Input file data definitions
        indata=self.A.Data
        self.iofile_bundle.Members['A'].data=indata
        indata=None #Clear variable to save memory

        # This could be a method somewhere
        for name, val in self.iofile_bundle.Members.items():
            if val.dir=='in':
                self.iofile_bundle.Members[name].write()

    def read_outfile(self):
        #Handle the ofiles here as you see the best
        a=self.iofile_bundle.Members['Z']
        a.read(dtype='object')
        self._Z.Data=a.data
        print(self._Z.Data)
        if self.par:
            self.queue.put(self._Z)

    def create_controlfile(self):
        self.control_in.Data.Members['control_file']=verilog_iofile(self,
            name='control_file',
            dir='in',
            iotype='ctrl'
        )
        # Create connectors of the signals controlled by this file
        # Connector list simpler to create with intermediate variable
        c=verilog_connector_bundle()
        siglist=[
               'reset',
               'initdone',
               'io_reference_addr',
               'io_reference_write_en',
               'io_estimate_addr',
               'io_estimate_write_en',
                ]
        siglist += ['io_reference_in_real'] 
        siglist += ['io_reference_in_imag']

        for name in siglist:
            c.new(name=name, cls='reg')

        self.control_in.Data.Members['control_file']\
                .verilog_connectors=c.list(names=siglist)

    def reset_sequence(self):
        #start defining the file
        f=self.control_in.Data.Members['control_file']
        f.set_control_data(init=0) #Initialize to zero at time 0
        step=int(1/(self.Rs*1e-12))

        time=0
        for name in [ 'reset', ]:
            f.set_control_data(time=time,name=name,val=1)

        # After awhile, switch off reset 
        time=int(16/(self.Rs*1e-12))

        for name in [ 'reset', ]:
            f.set_control_data(time=time,name=name,val=0)
        time+=step

        refseq=(np.array(PLPCsyn_long).reshape(-1,1)*(2**15-1)).astype(complex)
        print( refseq )
        f.set_control_data(time=time,name='io_reference_write_en',val=1)
        sequence=range(64)
        addr=0
        for i in range(64):
            time+=step
            f.set_control_data(time=time,name='io_reference_addr',val=i)
            f.set_control_data(time=time,name='io_reference_in_real',val=refseq[i].real)
            f.set_control_data(time=time,name='io_reference_in_imag',val=refseq[i].imag)
        time+=step
        f.set_control_data(time=time,name='io_reference_addr',val=0)
        f.set_control_data(time=time,name='io_reference_write_en',val=0)

        for name in [ 'initdone', ]:
            f.set_control_data(time=time,name=name,val=1)

    # Testbench definition method
    def define_testbench(self):
        #Initialize testbench
        self.tb=vtb(self)

        # Create TB connectors from the control file
        for connector in self.control_in.Data.Members['control_file'].verilog_connectors:
            self.tb.connectors.Members[connector.name]=connector
            # Connect them to DUT
            try: 
                self.dut.ios.Members[connector.name].connect=connector
            except:
                pass

        # Dut is created automaticaly, if verilog file for it exists
        self.tb.connectors.update(bundle=self.tb.dut_instance.io_signals.Members)

        #Assign verilog simulation parameters to testbench
        self.tb.parameters=self.vlogparameters

        # Copy iofile simulation parameters to testbench
        for name, val in self.iofile_bundle.Members.items():
            self.tb.parameters.Members.update(val.vlogparam)

        # Define the iofiles of the testbench. '
        # Needed for creating file io routines 
        self.tb.iofiles=self.iofile_bundle

        #Define testbench verilog file
        self.tb.file=self.vlogtbsrc


        ## Start initializations
        #Init the signals connected to the dut input to zero
        for name, val in self.tb.dut_instance.ios.Members.items():
            if val.cls=='input':
                val.connect.init='\'b0'

        # IO file connector definitions
        # Define what signals and in which order and format are read form the files
        # i.e. verilog_connectors of the file
        name='control_file'
        ionames=[
               'reset',
               'initdone',
               'io_reference_addr',
               'io_reference_write_en',
               'io_estimate_addr',
               'io_estimate_write_en',
                ]
        ionames += ['io_reference_in_real'] 
        ionames += ['io_reference_in_imag']

        self.iofile_bundle.Members[name].verilog_connectors=\
                self.tb.connectors.list(names=ionames)
        
        #for name in ionames:
        #    self.tb.connectors.Members[name].type='signed'

        name='A'
        ionames=[]
        ionames+=['io_A_real', 'io_A_imag' ]
        self.iofile_bundle.Members[name].verilog_connectors=\
                self.tb.connectors.list(names=ionames)

        name='Z'
        ionames=[]
        ionames+=['io_Z_real', 'io_Z_imag' ]
        self.iofile_bundle.Members[name].verilog_connectors=\
                self.tb.connectors.list(names=ionames)

        self.generate_tb_contents()

    def generate_tb_contents(self):
    # Start the testbench contents
        self.tb.contents="""
//timescale 1ps this should probably be a global model parameter
parameter integer c_Ts=1/(g_Rs*1e-12);
reg done;
"""+\
self.tb.connector_definitions+\
self.tb.iofile_definitions+\
"""

//DUT definition
"""+\
self.tb.dut_instance.instance+\
"""

//Master clock is omnipresent
always #(c_Ts/2.0) clock = !clock;

//Execution with parallel fork-join and sequential begin-end sections
initial #0 begin
fork
done=0;
""" + \
self.tb.connectors.verilog_inits(level=1)+\
"""
//io_out
$display("Ready to write");
@(posedge initdone) begin
    $display("Posedge initdone");
while (!done) begin
@(posedge clock ) begin
    //Print only valid values
    if ("""+\
            self.iofile_bundle.Members['Z'].verilog_io_condition +\
        """) begin
        """+\
            self.iofile_bundle.Members['Z'].verilog_io+\
        """
     end
end
end
end

    // Sequence triggered by initdone
    $display("Ready to read");
    @(posedge initdone ) begin
    $display("Posedge initdone");
        while (!$feof(f_A)) begin
             @(posedge clock )
             """+\
             self.iofile_bundle.Members['A'].verilog_io+\
             """
        end
        done<=1;
    end
begin
"""+\
self.iofile_bundle.Members['control_file'].verilog_io+\
"""
end
    join
    """+self.tb.iofile_close+"""
    $finish;
end"""

if __name__=="__main__":
    import matplotlib.pyplot as plt
    from  channel_equalizer import *
    dut=channel_equalizer()
    dut2=channel_equalizer()
    dut.model='py'
    dut2.model='sv'
    dut2.interactive_verilog=True
    len=16*64
    phres=64
    fsig=25e6
    indata=2**10*np.exp(1j*2*np.pi/phres*(np.arange(len)*np.round(fsig/dut.Rs*phres)))\
            .reshape(-1,1)
    dut.A.Data=indata
    dut2.A.Data=indata

    dut.run()
    dut2.run()
    #f0=plt.figure(0)
    #plt.plot(np.abs(dut._io_out.Data[10,:]))
    #plt.suptitle("Python model")
    #plt.xlabel("Freq")
    #plt.ylabel("Abs(FFT)")
    #plt.show(block=False)
    #f0.savefig('fft_python.eps', format='eps', dpi=300);
    #f1=plt.figure(1)
    #plt.plot(np.abs(dut2._io_out.Data[10,:]))
    #plt.suptitle("Verilog model")
    #plt.xlabel("Freq")
    #plt.ylabel("Abs(FFT)")
    #plt.show(block=False)
    #f1.savefig('fft_verilog.eps', format='eps', dpi=300);
    #input()

