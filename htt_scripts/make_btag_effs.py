#! /bin/env python
import rootpy.plotting.views as views
import rootpy.io as io
import os, glob
import rootpy
import URAnalysis.PlotTools.views as urviews
from pdb import set_trace
import itertools
rootpy.log["/"].setLevel(rootpy.log.INFO)
log = rootpy.log["/make_btag_effs.py"]
log.setLevel(rootpy.log.INFO)
from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument('tag', help='output file name')
#parser.add_argument('--pdfs', action='store_true', help='make plots for the PDF uncertainties')
args = parser.parse_args()

cut_scores = ['TIGHT', 'MEDIUM', 'LOOSE', 'NONE']
def scoring(name):
	for i, n in enumerate(cut_scores):
		if n in name: return i
	return len(cut_scores)

jet_types = [('bjet', 'bottom'), ('cjet', 'charm'), ('ljet', 'light')]

jobid = os.environ['jobid']
ura_proj = os.environ['URA_PROJECT']
input_file = '%s/results/%s/htt_flav_effs/ttJets.root' % (ura_proj, jobid)
tfile = io.root_open(input_file)

pt_bins  = [30.0, 35.0, 40.0, 45.0, 50.0, 55.0, 60.0, 65.0, 70.0, 75.0, 80.0, 85.0, 90.0, 95.0, 100.0, 110.0, 120.0, 130.0, 140.0, 150.0, 160.0, 170.0, 180.0, 190.0, 200.0, 210.0, 220.0, 230.0, 240.0, 250.0, 260.0, 270.0, 280.0, 290.0, 300.0, 310.0, 320.0, 330.0, 350.0, 370.0, 410.0, 600.0]#[30, 60, 100, 150, 200, 1000]
eta_bins = [-2.4, -1.8, -1.2, -0.6, 0.0, 0.6, 1.2, 1.8, 2.4]#[-2.4, -1.4, -0.8, 0.0, 0.8, 1.4, 2.4]
hview = urviews.RebinView(tfile, [pt_bins, eta_bins])
hview = views.SumView(
	views.SubdirectoryView(hview, 'electrons'),
	views.SubdirectoryView(hview, 'muons')
)
basedir = tfile.muons

def make_efficiency(hpass, hall):
	eff = hpass.Clone()
	eff.Reset()
	for bin_eff, bin_pass, bin_all in zip(eff, hpass, hall):
		if not bin_eff.overflow and bin_pass.value < 20:
			log.warning('bin (%.0f, %.2f) has %i entries' % (bin_eff.x.center, bin_eff.y.center, bin_pass.value))
		bin_eff.value = bin_pass.value/bin_all.value if bin_all.value else 0
		if bin_eff.value == 0 and not bin_eff.overflow:
			log.error('bin (%.0f, %.2f) has 0 efficiency' % (bin_eff.x.center, bin_eff.y.center))
	return eff

#ltypes = ['electrons', 'muons']
systypes = ['nosys']
selections = ['alljets']#, 'mtfail', 'mtpass']

for sysname, selection in itertools.product(systypes, selections):
	dirname = '/'.join([sysname, selection])
	tdir = basedir.Get(dirname)
	bids = list(set([i.name.split('_')[1] for i in tdir.keys()]))
	bids.sort(key=scoring)
	fname = '%s/inputs/%s/INPUT/htt_%s_%s_%s_efficiencies.root' % (
		ura_proj, jobid, args.tag, 
		bids[0], bids[1] if len(bids) == 2 else bids[0]
		)
	log.info('creating %s' % fname)
	with io.root_open(fname, 'w') as outfile:
		for jtype, dname in jet_types:
			jdir = outfile.mkdir(dname)
			jdir.cd()
			for cut_type in bids:
				log.info("computing efficiency for %s, %s jets" % (cut_type, jtype))
				h_all  = hview.Get('%s/btag_%s_%s_all'  % (dirname, cut_type, jtype))
				h_pass = hview.Get('%s/btag_%s_%s_pass' % (dirname, cut_type, jtype))
				eff = make_efficiency(h_pass, h_all)
				jdir.WriteTObject(eff, '%s_eff' % cut_type)

