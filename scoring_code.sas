proc sql; 
create table  &zbior._score as 
select indataset.*  
, case 
when act_age < 44.5 then 60.0 
when 44.5 <= act_age  and  act_age < 61.5 then 84.0 
when 61.5 <= act_age  and  act_age < 80.5 then 100.0 
when 80.5 <= act_age then 136.0 
else 60.0 end as PSC_act_age 
 
, case 
when 0.884 <= act_cc then 60.0 
when 0.622 <= act_cc  and  act_cc < 0.884 then 83.0 
when 0.549 <= act_cc  and  act_cc < 0.622 then 91.0 
when act_cc < 0.549 then 100.0 
else 60.0 end as PSC_act_cc 
 
, case 
when app_number_of_children < 0.5 then 60.0 
when 0.5 <= app_number_of_children  and  app_number_of_children < 1.5 then 66.0 
when 1.5 <= app_number_of_children  and  app_number_of_children < 2.5 then 83.0 
when 2.5 <= app_number_of_children then 121.0 
else 60.0 end as PSC_app_number_of_children 
 
, case 
when 0.5 <= act_ccss_n_statC  and  act_ccss_n_statC < 7.5 then 60.0 
when act_ccss_n_statC < 0.5 then 63.0 
when act_ccss_n_statC is null then 81.0 
when 7.5 <= act_ccss_n_statC  and  act_ccss_n_statC < 12.5 then 94.0 
when 12.5 <= act_ccss_n_statC then 133.0 
else 60.0 end as PSC_act_ccss_n_statC 
 
, case 
when 2.5 <= act_ccss_maxdue then 60.0 
when 1.5 <= act_ccss_maxdue  and  act_ccss_maxdue < 2.5 then 75.0 
when 0.5 <= act_ccss_maxdue  and  act_ccss_maxdue < 1.5 then 103.0 
when act_ccss_maxdue < 0.5 then 127.0 
when act_ccss_maxdue is null then 127.0 
else 60.0 end as PSC_act_ccss_maxdue 
 
, case 
when 5.5 <= act9_n_arrears then 60.0 
when 3.5 <= act9_n_arrears  and  act9_n_arrears < 5.5 then 76.0 
when 1.5 <= act9_n_arrears  and  act9_n_arrears < 3.5 then 86.0 
when act9_n_arrears < 1.5 then 97.0 
else 60.0 end as PSC_act9_n_arrears 
 
/* , 1/(1+exp(-(-0.03588230636718245*(0.0+ calculated PSC_act_age+ calculated PSC_act_cc+ calculated PSC_app_number_of_children+ calculated PSC_act_ccss_n_statC+ calculated PSC_act_ccss_maxdue+ calculated PSC_act9_n_arrears)+(18.570302372609376)))) as PD */ 
 
, 0.0 
+ calculated PSC_act_age + calculated PSC_act_cc + calculated PSC_app_number_of_children + calculated PSC_act_ccss_n_statC + calculated PSC_act_ccss_maxdue + calculated PSC_act9_n_arrears  as SCORECARD_POINTS 
 
from &zbior as indataset; 
quit; 
