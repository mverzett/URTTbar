#include <iostream>
#include "URAnalysis/AnalysisFW/interface/AnalyzerBase.h"
#include "Analyses/URTTbar/interface/URStreamer.h"
#include "URAnalysis/AnalysisFW/interface/URDriver.h"
#include "URAnalysis/AnalysisFW/interface/CutFlowTracker.h"
#include <boost/algorithm/string/predicate.hpp>
#include "URAnalysis/AnalysisFW/interface/URParser.h"
#include "URAnalysis/AnalysisFW/interface/DataFile.h"
#include "Analyses/URTTbar/interface/TTBarResponse.h"
#include "Analyses/URTTbar/interface/TTObjectSelector.h"
#include "Analyses/URTTbar/interface/TTBarPlots.h"
#include "Analyses/URTTbar/interface/TTBarSolver.h"
#include "Analyses/URTTbar/interface/TTGenParticleSelector.h"
#include "Analyses/URTTbar/interface/TTPermutator.h"
#include "Analyses/URTTbar/interface/TTGenMatcher.h"
#include "TRandom3.h"
#include "Analyses/URTTbar/interface/helper.h"
#include "URAnalysis/AnalysisFW/interface/RObject.h"
#include "Analyses/URTTbar/interface/systematics.h"
#include "Analyses/URTTbar/interface/MCWeightProducer.h"
#include "Analyses/URTTbar/interface/LeptonSF.h"
#include "Analyses/URTTbar/interface/Hypotheses.h"
#include "TROOT.h"
//#include <map>

using namespace std;

class permProbComputer : public AnalyzerBase
{
public:
	enum TTNaming {RIGHT, RIGHT_THAD, RIGHT_TLEP, WRONG, OTHER, NOTSET};
private:
	//histograms and helpers
	CutFlowTracker tracker_;
  vector<string> dir_names_ = {"semilep_visible_right", "semilep_right_thad", "semilep_right_tlep", "semilep_wrong", "other_tt_decay"};
  //histos
  map<systematics::SysShifts, map<TTNaming, map<string, RObject> > > histos_;


	//switches
	bool isTTbar_, skew_tt_distro_=false;

  //selectors and helpers
  TTGenParticleSelector genp_selector_;
  TTObjectSelector object_selector_;
  TTPermutator permutator_;
  TTGenMatcher matcher_;
  TTBarSolver solver_;
  float evt_weight_;
	TRandom3 randomizer_;// = TRandom3(98765);
  MCWeightProducer mc_weights_;

	vector<systematics::SysShifts> systematics_;

	//Scale factors
  LeptonSF electron_sf_, muon_sf_;
  
public:
  permProbComputer(const std::string output_filename):
    AnalyzerBase("permProbComputer", output_filename),
		tracker_(),
    object_selector_(),
    permutator_(),
    matcher_(),
    solver_(),
    evt_weight_(1.),
    mc_weights_(),
    electron_sf_("electron_sf", false),
    muon_sf_("muon_sf"){
    
    //tracker_.verbose(true);    
    //set tracker
    tracker_.use_weight(&evt_weight_);
    object_selector_.set_tracker(&tracker_);
    permutator_.set_tracker(&tracker_);

    opts::variables_map &values = URParser::instance().values();

    //switches
    skew_tt_distro_ = values["general.skew_ttpt_distribution"].as<int>();

    //find out which sample are we running on
		string output_file = values["output"].as<std::string>();
    //DataFile solver_input(values["general.ttsolver_input"].as<std::string>());
		string sample = systematics::get_sample(output_file);
    bool isSignal = boost::starts_with(sample, "AtoTT") || boost::starts_with(sample, "HtoTT");
		isTTbar_ = boost::starts_with(sample, "ttJets") || isSignal;

    //choose systematics to run based on sample
    systematics_ = systematics::get_systematics(output_file);
    if(!isTTbar_) {
      Logger::log().error() << "This analyzer is only supposed to run on ttbar samples!" << endl;
      throw 49;
    }
    
    //Do not init the solver, as we do not have the files! 
    if(values["general.pseudotop"].as<int>() == 0) genp_selector_ = TTGenParticleSelector(); //TTGenParticleSelector::SelMode::LHE); //FIXME allow for herwig setting
    else genp_selector_ = TTGenParticleSelector(TTGenParticleSelector::SelMode::PSEUDOTOP);

    solver_.Init("", false, false, false);

    mc_weights_.init(sample);
  };
  
  ~permProbComputer() {
  }

  //This method is called once per job at the beginning of the analysis
  //book here your histograms/tree and run every initialization needed
  virtual void begin() {
    outFile_.cd();
    vector<TTNaming> evt_types = {RIGHT, RIGHT_THAD, RIGHT_TLEP, WRONG, OTHER};
    for(auto evt_type : evt_types){
      TDirectory* dir_type = outFile_.mkdir(dir_names_[evt_type].c_str());
      dir_type->cd();
      for(auto shift : systematics_) {
        TDirectory* dir_sys = dir_type->mkdir(systematics::shift_to_name.at(shift).c_str());
        dir_sys->cd();
        //TODO add plots
        histos_[shift][evt_type]["mWhad_vs_mtophad"] = RObject::book<TH2D>("mWhad_vs_mtophad", ";M(W_{had}) [GeV];M(t_{had}) [GeV]", 500, 0., 500., 500, 0., 500);
        histos_[shift][evt_type]["nusolver_chi2"] = RObject::book<TH1D>("nusolver_chi2", "#chi^{2};# Events", 75, 0., 150.);
        histos_[shift][evt_type]["wfr_jcosth_delta"] = RObject::book<TH1D>("wfr_jcosth_delta", "", 100, 0., 2);

        histos_[shift][evt_type]["thfr"] = RObject::book<TH1D>("thfr", "", 100, -2., 2);
        histos_[shift][evt_type]["tlfr"] = RObject::book<TH1D>("tlfr", "", 100, -2., 2);
        if(evt_type == RIGHT || evt_type == WRONG){
          histos_[shift][evt_type]["btag_value"] = RObject::book<TH1D>("btag_value", ";CSV raw value;# Events", 100, 0., 1.);
          histos_[shift][evt_type]["btag_first_idx"] = RObject::book<TH1D>("btag_first_idx", ";idx;# Events", 41, -0.5, 40.5);
          histos_[shift][evt_type]["btag_last_idx"] = RObject::book<TH1D>("btag_last_idx", ";idx;# Events", 41, -0.5, 40.5);
          histos_[shift][evt_type]["pt_first_idx"] = RObject::book<TH1D>("pt_first_idx", ";idx;# Events", 41, -0.5, 40.5);
          histos_[shift][evt_type]["pt_last_idx"] = RObject::book<TH1D>("pt_last_idx", ";idx;# Events", 41, -0.5, 40.5);
        }
      }
    }

  }
  
  void process_evt(URStreamer &event, systematics::SysShifts shift=systematics::SysShifts::NOSYS) {
    //Fill truth of resp matrix
    GenTTBar &ttbar = genp_selector_.ttbar_system();
    if(skew_tt_distro_) evt_weight_ *= 1.+0.05*(ttbar.top.Pt()-200.)/1000.;
 
    //select reco objects
    if( !object_selector_.select(event, shift) ) return;
    tracker_.track("obj selection");

    //find mc weight
    if(object_selector_.tight_muons().size() == 1)
      evt_weight_ *= muon_sf_.get_sf(object_selector_.lepton()->Pt(), object_selector_.lepton()->Eta());
    if(object_selector_.tight_electrons().size() == 1)
      evt_weight_ *= electron_sf_.get_sf(object_selector_.lepton()->Pt(), object_selector_.lepton()->Eta());
    tracker_.track("MC weights");

    bool preselection_pass = permutator_.preselection(
      object_selector_.clean_jets(), object_selector_.lepton(), object_selector_.met()
      );
    tracker_.track("permutation pre-selection done (not applied)");

    //get needed histo map
    auto plots = histos_.find(shift)->second;    

    if( !preselection_pass ) return;
    tracker_.track("perm preselection");

    //Gen matching
    Permutation matched_perm;
    if(ttbar.type == GenTTBar::DecayType::SEMILEP) {
      matched_perm = matcher_.match(
        genp_selector_.ttbar_final_system(),
        object_selector_.clean_jets(), 
        object_selector_.veto_electrons(),
        object_selector_.veto_muons()
        );
    }
    matched_perm.SetMET(object_selector_.met());
    tracker_.track("gen matching");

    //get selected jets
    auto jets = object_selector_.clean_jets();
		IDJet* bhad = matched_perm.BHad();
		IDJet* blep = matched_perm.BLep();
    if(matched_perm.BHad()) plots[TTNaming::RIGHT]["btag_value"].fill(bhad->csvIncl(), evt_weight_);
    if(matched_perm.BLep()) plots[TTNaming::RIGHT]["btag_value"].fill(blep->csvIncl(), evt_weight_);

    //fill wrong btags and pt indexes
    bool right_1st=false, wrong_1st=false;
    size_t idx=0, right_last=4000, wrong_last=4000;
    sort(jets.begin(), jets.end(), [](IDJet* A, IDJet* B){return(A->Pt() > B->Pt());});
    for(IDJet* jet : jets) {
      if(jet != bhad && jet != blep) {
        plots[TTNaming::WRONG]["btag_value"].fill(jet->csvIncl(), evt_weight_);
        if(!wrong_1st){
          plots[TTNaming::WRONG]["pt_first_idx"].fill(idx, evt_weight_);
          wrong_1st=true;
        }
        wrong_last=idx;
      }
      else {
        if(!right_1st){
          plots[TTNaming::RIGHT]["pt_first_idx"].fill(idx, evt_weight_);
          right_1st=true;
        }
        right_last=idx;
      }
      
      idx++;
    }
    plots[TTNaming::WRONG]["pt_last_idx"].fill(wrong_last, evt_weight_);
    plots[TTNaming::RIGHT]["pt_last_idx"].fill(right_last, evt_weight_);

    //fill btag indexes
    right_1st=false; wrong_1st=false;
    idx=0; right_last=4000; wrong_last=4000;
    sort(jets.begin(), jets.end(), [](IDJet* A, IDJet* B){return(A->csvIncl() < B->csvIncl());});//larger first
    for(IDJet* jet : jets) {
      if(jet != bhad && jet != blep) {
        if(!wrong_1st){
          plots[TTNaming::WRONG]["btag_first_idx"].fill(idx, evt_weight_);
          wrong_1st=true;
        }
        wrong_last=idx;
      }
      else {
        if(!right_1st){
          plots[TTNaming::RIGHT]["btag_first_idx"].fill(idx, evt_weight_);
          right_1st=true;
        }
        right_last=idx;
      }
      
      idx++;
    }
    plots[TTNaming::WRONG]["btag_last_idx"].fill(wrong_last, evt_weight_);
    plots[TTNaming::RIGHT]["btag_last_idx"].fill(right_last, evt_weight_);
    tracker_.track("btag and pt idx plots");
    
    //Find best permutation
    bool go_on = true;
    while(go_on) {
      Permutation test_perm = permutator_.next(go_on);
      if(go_on) {
				test_perm.LepCharge(object_selector_.lepton_charge());
        test_perm.Solve(solver_);
        TTNaming perm_status;
        if(test_perm.IsCorrect(matched_perm)) perm_status = TTNaming::RIGHT;
        else if(test_perm.IsTHadCorrect(matched_perm)) perm_status = TTNaming::RIGHT_THAD;
        else if(test_perm.IsBLepCorrect(matched_perm)) perm_status = TTNaming::RIGHT_TLEP;
        else if(ttbar.type == GenTTBar::DecayType::SEMILEP) perm_status = TTNaming::WRONG;
        else perm_status = TTNaming::OTHER;
        
        plots[perm_status]["mWhad_vs_mtophad"].fill(test_perm.WHad().M(), test_perm.THad().M(), evt_weight_);
        plots[perm_status]["nusolver_chi2"].fill(test_perm.NuChisq(), evt_weight_);
				
				hyp::TTbar ttang(test_perm);
				auto hadwcm = ttang.thad().W().to_CM();
				auto leptcm = ttang.tlep().to_CM();
				auto hadtcm = ttang.thad().to_CM();				
				auto ttcm   = ttang.to_CM();

				double cj1 = hadtcm.W().unit3D().Dot(hadwcm.down().unit3D());
				double cj2 = hadtcm.W().unit3D().Dot(hadwcm.up().unit3D());
				double cjm = (cj1 < cj2) ? cj1 : cj2;
				double cjM = (cj1 > cj2) ? cj1 : cj2;

				double cwl = leptcm.W().unit3D().Dot(ttcm.tlep().unit3D());
				double cwh = hadtcm.W().unit3D().Dot(ttcm.thad().unit3D());

				double cbl = leptcm.b().unit3D().Dot(ttcm.tlep().unit3D());
				double cbh = hadtcm.b().unit3D().Dot(ttcm.thad().unit3D());

        plots[perm_status]["wfr_jcosth_delta"].fill(cjM-cjm, evt_weight_);
        plots[perm_status]["thfr"].fill(cbh - cwh, evt_weight_);
        plots[perm_status]["tlfr"].fill(cbl - cwl, evt_weight_);
      }
    }
    tracker_.track("end");
  }

  //This method is called once every file, contains the event loop
  //run your proper analysis here
  virtual void analyze()
  {
		unsigned long evt_idx = 0;
    URStreamer event(tree_);

    Logger::log().debug() << "--retrieving running conditions--" << endl;
    opts::variables_map &values = URParser::instance().values();
		int limit = values["limit"].as<int>();
		int skip  = values["skip"].as<int>();
    int report = values["report"].as<int>();
    Logger::log().debug() << "-- DONE -- reporting every -- " << report << endl;
    while(event.next()) {
			if(limit > 0 && evt_idx > limit) {
				return;
			}
			evt_idx++;
			if(skip > 0 && evt_idx < skip) {
				continue;
			}
			if(evt_idx % report == 0) Logger::log().debug() << "Beginning event " << evt_idx << " run: " << event.run << " lumisection: " << event.lumi << " eventnumber: " << event.evt << endl;
      tracker_.track("start");		 

			//long and time consuming
			if(isTTbar_){
        bool selection = 	genp_selector_.select(event);			
        tracker_.track("gen selection");        
        if(!selection) {
          Logger::log().error() << "Error: TTGenParticleSelector was not able to find all the generated top decay products in event " << evt_idx << endl <<
            "run: " << event.run << " lumisection: " << event.lumi << " eventnumber: " << event.evt << endl;
          continue;
        }
			}
	
      tracker_.deactivate();    
			for(auto shift : systematics_){
        evt_weight_ = mc_weights_.evt_weight(event, shift);
				if(shift == systematics::SysShifts::NOSYS) tracker_.activate();
				//Logger::log().debug() << "processing: " << shift << endl;
				process_evt(event, shift);
				if(shift == systematics::SysShifts::NOSYS) tracker_.deactivate();
			}

    }  //while(event.next())
  }

  //this method is called at the end of the job, by default saves
  //every histogram/tree produced, override it if you need something more
  virtual void end(){
		outFile_.Write();
		tracker_.writeTo(outFile_);
	}

  //do you need command-line or cfg options? If so implement this 
  //method to book the options you need. CLI parsing is provided
  //by AnalysisFW/interface/URParser.h and uses boost::program_options
  //look here for a quickstart tutorial: 
  //http://www.boost.org/doc/libs/1_51_0/doc/html/program_options/tutorial.html
  static void setOptions() {
    URParser &parser = URParser::instance();
    parser.addCfgParameter<int>("general", "skew_ttpt_distribution", "Should I skew the pt distribution? (0/1)");
    parser.addCfgParameter<int>("general", "pseudotop", "should I use pseudo-top? (0/1)");

		opts::options_description &opts = parser.optionGroup("analyzer", "CLI and CFG options that modify the analysis");
		opts.add_options()
      ("limit,l", opts::value<int>()->default_value(-1), "limit the number of events processed per file")
      ("skip,s", opts::value<int>()->default_value(-1), "limit the number of events processed per file")
      ("report", opts::value<int>()->default_value(10000), "report every in debug mode");
  }
};

//make it executable
int main(int argc, char *argv[])
{
  URParser &parser = URParser::instance(argc, argv);
  URDriver<permProbComputer> test;
	int excode = test.run();
	//Logger::log().debug() << "RUNNING DONE " << std::endl;
	auto files = gROOT->GetListOfFiles(); //make ROOT aware that some files do not exist, because REASONS
	Logger::log().debug() << "Nfiles " << files->GetSize() << std::endl; //need to print out this otherwise ROOT loses its shit in 7.4.X (such I/O, much features)
  return excode;
}
