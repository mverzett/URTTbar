#include "TTGenMatcher.h"
#include "GenObject.h"
#include "URParser.h"

const map<std::string, TTGenMatcher::MatchMode> TTGenMatcher::name_to_mode = {
  {"DR_DR", TTGenMatcher::MatchMode::DR_DR}, 
  {"DR_DPT", TTGenMatcher::MatchMode::DR_DPT}, 
  {"DR_PTMAX", TTGenMatcher::MatchMode::DR_PTMAX}
};

TTGenMatcher::TTGenMatcher() {
  URParser &parser = URParser::instance();
  parser.addCfgParameter<float>("gen_matching", "drmax", "minimum DR", 0.3);
  parser.addCfgParameter<std::string>("gen_matching", "mode", "matching mode, can be DR_DR, DR_DPT, DR_PTMAX", "DR_PTMAX");

  parser.parseArguments();
  parser.parseArguments();

  max_dr_ = parser.getCfgPar<float>("gen_matching", "drmax");
  mode_ = TTGenMatcher::name_to_mode.at( parser.getCfgPar<std::string>("gen_matching", "mode") );
}

Permutation TTGenMatcher::match(GenTTBar& gen_hyp, std::vector<IDJet*> &jets, 
                                std::vector<IDElectron*> &electrons, std::vector<IDMuon*> &muons) {
	Permutation ret;
	if(gen_hyp.type != GenTTBar::DecayType::SEMILEP) return ret;

	ret.BHad( gen_match(gen_hyp.had_b(), jets) );
	ret.BLep( gen_match(gen_hyp.lep_b(), jets) );
	const GenObject* lepton = gen_hyp.lepton();

	ret.WJa( gen_match(gen_hyp.had_W()->first , jets) );
	ret.WJb( gen_match(gen_hyp.had_W()->second, jets) );

	if(fabs(lepton->pdgId()) == ura::PDGID::e){
		ret.L( gen_match(lepton, electrons) );
	}else{
		ret.L( gen_match(lepton, muons) );
	}
	//neutrino is not set
	return ret;
}
