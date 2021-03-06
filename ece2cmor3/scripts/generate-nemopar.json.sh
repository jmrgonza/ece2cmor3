#!/bin/bash
# Thomas Reerink
#
# This scripts requires 1 argument:
#
# ${1} the first argument is the ouput file: the new nemopar.json file.
#
# Run example:
#  ./generate-nemopar.json.sh new-nemopar.json
#

# The default example list for this moment could be produced by running:
#  more nemopar.json |grep -e target | sed -e 's/.*://'
# And pasting the result here in the arr array.

# The current list is in the arr array is produced by running:
#  more ~/cmorize/shaconemo/ping-files/r255/cmor-varlist-based-on-ping-r255-without-dummy-lines.txt | sed -e 's/^/"/'  -e 's/$/"/' > tmp.txt
# And pasting the result here.

# Declare an array variable with all the nemo cmor variable names:
declare -a arr=(
"agessc"
"areacello"
"basin"
"bigthetao"
"bigthetaoga"
"cfc11"
"cfc12"
"deptho"
"diftrblo2d"
"diftrelo2d"
"diftrxylo2d"
"difvho"
"difvmo"
"difvmto"
"difvso"
"difvtrto"
"dispkevfo"
"dispkexyfo2d"
"evs"
"fgcfc11"
"fgcfc12"
"fgsf6"
"ficeberg2d"
"flandice"
"friver"
"fsitherm"
"hcont300"
"hfbasin"
"hfbasinpmadv"
"hfds"
"hfevapds"
"hfgeou"
"hfibthermds2d"
"hfrainds"
"hfrunoffds2d"
"hfsnthermds2d"
"hfx"
"hfy"
"htovgyre"
"htovovrt"
"masscello"
"masso"
"mfo"
"mlotst"
"mlotstmax"
"mlotstmin"
"mlotstsq"
"msftbarot"
"msftyz"
"obvfsq"
"ocontempdiff"
"ocontemppadvect"
"ocontemppmdiff"
"ocontemprmadvect"
"ocontemptend"
"omldamax"
"osaltdiff"
"osaltpadvect"
"osaltpmdiff"
"osaltrmadvect"
"osalttend"
"pbo"
"rsdo"
"rsntds"
"sf6"
"sfdsi"
"sftof"
"sltbasin"
"sltnortha"
"sltovgyre"
"sltovovrt"
"so"
"sob"
"soga"
"somint"
"sos"
"sosga"
"sossq"
"t20d"
"tauuo"
"tauvo"
"thetao"
"thetaoga"
"thetaot"
"thetaot2000"
"thetaot300"
"thetaot700"
"thkcello"
"tnkebto2d"
"tnpeo"
"tob"
"tomint"
"tos"
"tosga"
"tossq"
"umo"
"uo"
"vmo"
"vo"
"volo"
"wfonocorr"
"wmo"
"wo"
"zos"
"zossq"
"zostoga"
"bfe"
"bfeos"
"bsi"
"bsios"
"calc"
"chl"
"chldiat"
"chldiatos"
"chlmisc"
"chlmiscos"
"chlos"
"co3"
"co3satcalc"
"dcalc"
"detoc"
"dfe"
"dfeos"
"dissic"
"dissicos"
"dissoc"
"dpco2"
"dpo2"
"epc100"
"epcalc100"
"epfe100"
"epsi100"
"expc"
"expcalc"
"expfe"
"expsi"
"fbddtalk"
"fbddtdic"
"fbddtdife"
"fbddtdin"
"fbddtdip"
"fbddtdisi"
"fgco2"
"fgo2"
"fric"
"froc"
"fsfe"
"fsn"
"graz"
"intdic"
"intpbfe"
"intpbsi"
"intpn2"
"intpp"
"intppdiat"
"intppmisc"
"intppnitrate"
"limfediat"
"limfemisc"
"limirrdiat"
"limirrmisc"
"limndiat"
"limnmisc"
"nh4"
"no3"
"no3os"
"o2"
"o2min"
"o2os"
"pbfe"
"pbsi"
"pcalc"
"pdi"
"ph"
"phyc"
"phycos"
"phydiat"
"phyfe"
"phyfeos"
"phymisc"
"physi"
"physios"
"pnitrate"
"po4"
"poc"
"pocos"
"pp"
"ppdiat"
"ppmisc"
"remoc"
"si"
"sios"
"spco2"
"talk"
"zmeso"
"zmicro"
"zo2min"
"zooc"
"siage"
"siareaacrossline"
"siarean"
"siareas"
"sicompstren"
"siconc"
"sidconcdyn"
"sidconcth"
"sidivvel"
"sidmassdyn"
"sidmassevapsubl"
"sidmassgrowthbot"
"sidmassgrowthwat"
"sidmassmeltbot"
"sidmassmelttop"
"sidmasssi"
"sidmassth"
"sidmasstranx"
"sidmasstrany"
"siextentn"
"siextents"
"sifb"
"siflcondbot"
"siflcondtop"
"siflfwbot"
"siflfwdrain"
"siflsaltbot"
"siflsensupbot"
"siforcecoriolx"
"siforcecorioly"
"siforceintstrx"
"siforceintstry"
"siforcetiltx"
"siforcetilty"
"sihc"
"siitdconc"
"siitdsnthick"
"siitdthick"
"simass"
"simassacrossline"
"sisali"
"sisaltmass"
"sishevel"
"sisnhc"
"sisnmass"
"sisnthick"
"sispeed"
"sistremax"
"sistresave"
"sistrxdtop"
"sistrxubot"
"sistrydtop"
"sistryubot"
"sitempbot"
"sitempsnic"
"sitemptop"
"sithick"
"sitimefrac"
"siu"
"siv"
"sivol"
"sivoln"
"sivols"
"sndmassdyn"
"sndmassmelt"
"sndmasssi"
"sndmasssnf"
"sndmasssubl"
"snmassacrossline"
)


function add_item {
 echo '    {'                     >> ${output_file}
 echo '        "source": "'$1'",' >> ${output_file}
 echo '        "target": "'$1'"'  >> ${output_file}
 echo '    },'                    >> ${output_file}
}

function add_last_item {
 echo '    {'                     >> ${output_file}
 echo '        "source": "'$1'",' >> ${output_file}
 echo '        "target": "'$1'"'  >> ${output_file}
 echo '    }'                     >> ${output_file}
}


if [ "$#" -eq 1 ]; then
 output_file=$1


 echo '['                         > ${output_file}

 # Loop through the array with all the nemo cmor variable names:
 # (Note individual array elements can be accessed by using "${arr[0]}", "${arr[1]}")
 
 N=${#arr[@]} # array length
 last_item="${arr[N-1]}"
#echo ${N} ${last_item}
 for i in "${arr[@]}"
 do
    if [ "$i" == ${last_item} ]; then
     add_last_item "$i"
    else
     add_item "$i"
    fi
 done

 echo ']'                         >> ${output_file}


 echo ' The file ' ${output_file} ' is created.'

else
    echo '  '
    echo '  This scripts requires one argument, e.g.:'
    echo '  ' $0 no-grid-nemopar.json
    echo '  '
fi
