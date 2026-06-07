proc sql; 
create table  &zbior._score as 
select indataset.*  
, case 
when 48.5 <= act_age  and  act_age < 57.5 then 4.0 
when act_age < 48.5 then 18.0 
when 70.500 <= act_age then 23.0 
when 57.5 <= act_age  and  act_age < 70.5 then 30.0 
else 4.0 end as PSC_act_age 
 
, case 
when 0.809 <= act_cc then 4.0 
when 0.548 <= act_cc  and  act_cc < 0.728 then 6.0 
when 0.728 <= act_cc  and  act_cc < 0.809 then 10.0 
when act_cc < 0.548 then 13.0 
else 4.0 end as PSC_act_cc 
 
, case 
when 4.696 <= act_loaninc then 4.0 
when 3.648 <= act_loaninc  and  act_loaninc < 4.291 then 5.0 
when act_loaninc < 3.648 then 8.0 
when 4.291 <= act_loaninc  and  act_loaninc < 4.696 then 13.0 
else 4.0 end as PSC_act_loaninc 
 
, case 
when app_income < 582.5 then 4.0 
when 582.5 <= app_income  and  app_income < 1064.5 then 16.0 
when 2126.500 <= app_income then 18.0 
when 1064.5 <= app_income  and  app_income < 2126.5 then 27.0 
else 4.0 end as PSC_app_income 
 
, case 
when 18 <= app_n_installments  and  app_n_installments < 30 then 4.0 
when 30.000 <= app_n_installments then 6.0 
when app_n_installments < 18 then 7.0 
else 4.0 end as PSC_app_n_installments 
 
, case 
when app_number_of_children < 0.5 then 4.0 
when 0.5 <= app_number_of_children  and  app_number_of_children < 1.5 then 11.0 
when 1.5 <= app_number_of_children  and  app_number_of_children < 2.5 then 23.0 
when 2.500 <= app_number_of_children then 64.0 
else 4.0 end as PSC_app_number_of_children 
 
, case 
when 199.5 <= app_installment  and  app_installment < 208.5 then 4.0 
when 121.5 <= app_installment  and  app_installment < 199.5 then 26.0 
when 208.500 <= app_installment then 26.0 
when app_installment < 121.5 then 34.0 
else 4.0 end as PSC_app_installment 
 
, case 
when 1.477 <= act_call_cc then 4.0 
when 0.75 <= act_call_cc  and  act_call_cc < 0.979 then 4.0 
when 0.979 <= act_call_cc  and  act_call_cc < 1.477 then 11.0 
when act_call_cc < 0.75 then 14.0 
else 4.0 end as PSC_act_call_cc 
 
, case 
when act_cins_n_loan < 0.5 then 4.0 
when 1.500 <= act_cins_n_loan then 4.0 
when 0.5 <= act_cins_n_loan  and  act_cins_n_loan < 1.5 then 5.0 
else 4.0 end as PSC_act_cins_n_loan 
 
, case 
when 16.5 <= act_cins_min_seniority  and  act_cins_min_seniority < 31.5 then 4.0 
when act_cins_min_seniority < 16.5 then 8.0 
when 31.5 <= act_cins_min_seniority  and  act_cins_min_seniority < 55.5 then 9.0 
when act_cins_min_seniority is null then 12.0 
when 55.500 <= act_cins_min_seniority then 19.0 
else 4.0 end as PSC_act_cins_min_seniority 
 
, case 
when 0.5 <= act_cins_n_statC  and  act_cins_n_statC < 1.5 then 4.0 
when act_cins_n_statC < 0.5 then 5.0 
when 1.5 <= act_cins_n_statC  and  act_cins_n_statC < 2.5 then 5.0 
when 2.500 <= act_cins_n_statC then 6.0 
when act_cins_n_statC is null then 7.0 
else 4.0 end as PSC_act_cins_n_statC 
 
, case 
when 1.500 <= act_cins_n_statB then 4.0 
when act_cins_n_statB < 0.5 then -5.0 
when 0.5 <= act_cins_n_statB  and  act_cins_n_statB < 1.5 then -13.0 
when act_cins_n_statB is null then -47.0 
else 4.0 end as PSC_act_cins_n_statB 
 
, case 
when act_cins_n_loans_act < 1.5 then 4.0 
when 1.500 <= act_cins_n_loans_act then -7.0 
when act_cins_n_loans_act is null then -24.0 
else 4.0 end as PSC_act_cins_n_loans_act 
 
, case 
when 0.500 <= act_cins_maxdue then 4.0 
when act_cins_maxdue < 0.5 then 32.0 
when act_cins_maxdue is null then 48.0 
else 4.0 end as PSC_act_cins_maxdue 
 
, case 
when 23.500 <= act_cins_min_pninst then 4.0 
when 11.5 <= act_cins_min_pninst  and  act_cins_min_pninst < 21.5 then 7.0 
when 21.5 <= act_cins_min_pninst  and  act_cins_min_pninst < 23.5 then 15.0 
when act_cins_min_pninst < 11.5 then 17.0 
when act_cins_min_pninst is null then 23.0 
else 4.0 end as PSC_act_cins_min_pninst 
 
, case 
when 0.986 <= act_cins_utl then 4.0 
when 0.439 <= act_cins_utl  and  act_cins_utl < 0.844 then 13.0 
when 0.844 <= act_cins_utl  and  act_cins_utl < 0.986 then 18.0 
when act_cins_utl < 0.439 then 22.0 
when act_cins_utl is null then 30.0 
else 4.0 end as PSC_act_cins_utl 
 
, case 
when 0.575 <= act_cins_cc then 4.0 
when act_cins_cc < 0.29 then 10.0 
when 0.47 <= act_cins_cc  and  act_cins_cc < 0.575 then 11.0 
when 0.29 <= act_cins_cc  and  act_cins_cc < 0.47 then 19.0 
when act_cins_cc is null then 22.0 
else 4.0 end as PSC_act_cins_cc 
 
, case 
when act_ccss_seniority < 31.5 then 4.0 
when 31.5 <= act_ccss_seniority  and  act_ccss_seniority < 42.5 then 4.0 
when 42.5 <= act_ccss_seniority  and  act_ccss_seniority < 128.5 then 4.0 
when act_ccss_seniority is null then 4.0 
when 128.500 <= act_ccss_seniority then 4.0 
else 4.0 end as PSC_act_ccss_seniority 
 
, case 
when 4.5 <= act_ccss_min_seniority  and  act_ccss_min_seniority < 16.5 then 4.0 
when 16.5 <= act_ccss_min_seniority  and  act_ccss_min_seniority < 33.5 then -4.0 
when act_ccss_min_seniority < 4.5 then -6.0 
when act_ccss_min_seniority is null then -9.0 
when 33.500 <= act_ccss_min_seniority then -11.0 
else 4.0 end as PSC_act_ccss_min_seniority 
 
, case 
when act_ccss_n_statC < 1.5 then 4.0 
when 1.5 <= act_ccss_n_statC  and  act_ccss_n_statC < 6.5 then 6.0 
when act_ccss_n_statC is null then 28.0 
when 6.5 <= act_ccss_n_statC  and  act_ccss_n_statC < 10.5 then 36.0 
when 10.500 <= act_ccss_n_statC then 76.0 
else 4.0 end as PSC_act_ccss_n_statC 
 
, case 
when 6.500 <= act_ccss_n_statB then 4.0 
when 3.5 <= act_ccss_n_statB  and  act_ccss_n_statB < 6.5 then 4.0 
when act_ccss_n_statB < 0.5 then 3.0 
when 0.5 <= act_ccss_n_statB  and  act_ccss_n_statB < 3.5 then 3.0 
when act_ccss_n_statB is null then 3.0 
else 4.0 end as PSC_act_ccss_n_statB 
 
, case 
when 3.5 <= act_ccss_min_pninst  and  act_ccss_min_pninst < 11.5 then 4.0 
when 11.500 <= act_ccss_min_pninst then 1.0 
when act_ccss_min_pninst < 2.5 then 1.0 
when 2.5 <= act_ccss_min_pninst  and  act_ccss_min_pninst < 3.5 then -7.0 
when act_ccss_min_pninst is null then -7.0 
else 4.0 end as PSC_act_ccss_min_pninst 
 
, case 
when 6.500 <= act_ccss_min_lninst then 4.0 
when 3.5 <= act_ccss_min_lninst  and  act_ccss_min_lninst < 6.5 then 9.0 
when 1.5 <= act_ccss_min_lninst  and  act_ccss_min_lninst < 3.5 then 18.0 
when act_ccss_min_lninst is null then 23.0 
when act_ccss_min_lninst < 1.5 then 31.0 
else 4.0 end as PSC_act_ccss_min_lninst 
 
, case 
when 0.023 <= act_ccss_dueutl then 4.0 
when 0.009 <= act_ccss_dueutl  and  act_ccss_dueutl < 0.023 then 5.0 
when act_ccss_dueutl < 0.003 then 9.0 
when act_ccss_dueutl is null then 10.0 
when 0.003 <= act_ccss_dueutl  and  act_ccss_dueutl < 0.009 then 13.0 
else 4.0 end as PSC_act_ccss_dueutl 
 
, case 
when 0.748 <= act_ccss_cc  and  act_ccss_cc < 0.981 then 4.0 
when act_ccss_cc < 0.748 then 5.0 
when 0.981 <= act_ccss_cc  and  act_ccss_cc < 1.369 then 7.0 
when act_ccss_cc is null then 9.0 
when 1.369 <= act_ccss_cc then 9.0 
else 4.0 end as PSC_act_ccss_cc 
 
, case 
when agr3_Min_CMaxI_Days < 8.5 then 4.0 
when 9.5 <= agr3_Min_CMaxI_Days  and  agr3_Min_CMaxI_Days < 11.5 then 4.0 
when 8.5 <= agr3_Min_CMaxI_Days  and  agr3_Min_CMaxI_Days < 9.5 then 4.0 
when 11.500 <= agr3_Min_CMaxI_Days then 4.0 
when agr3_Min_CMaxI_Days is null then 3.0 
else 4.0 end as PSC_agr3_Min_CMaxI_Days 
 
, case 
when 0.500 <= ags3_Max_CMaxI_Due then 4.0 
when ags3_Max_CMaxI_Due < 0.5 then -12.0 
when ags3_Max_CMaxI_Due is null then -27.0 
else 4.0 end as PSC_ags3_Max_CMaxI_Due 
 
, case 
when ags3_Mean_CMaxC_Days < 13.833 then 4.0 
when 13.833 <= ags3_Mean_CMaxC_Days  and  ags3_Mean_CMaxC_Days < 14.167 then 2.0 
when 14.167 <= ags3_Mean_CMaxC_Days  and  ags3_Mean_CMaxC_Days < 14.583 then 1.0 
when ags3_Mean_CMaxC_Days is null then -2.0 
when 14.583 <= ags3_Mean_CMaxC_Days then -2.0 
else 4.0 end as PSC_ags3_Mean_CMaxC_Days 
 
, case 
when 1.167 <= ags3_Mean_CMaxC_Due then 4.0 
when 0.833 <= ags3_Mean_CMaxC_Due  and  ags3_Mean_CMaxC_Due < 1.167 then 2.0 
when 0.583 <= ags3_Mean_CMaxC_Due  and  ags3_Mean_CMaxC_Due < 0.833 then 0.0 
when ags3_Mean_CMaxC_Due < 0.583 then -2.0 
when ags3_Mean_CMaxC_Due is null then -4.0 
else 4.0 end as PSC_ags3_Mean_CMaxC_Due 
 
, case 
when ags3_Mean_CMaxA_Days < 14.167 then 4.0 
when 14.167 <= ags3_Mean_CMaxA_Days  and  ags3_Mean_CMaxA_Days < 14.583 then 3.0 
when 14.583 <= ags3_Mean_CMaxA_Days  and  ags3_Mean_CMaxA_Days < 14.833 then 3.0 
when 14.833 <= ags3_Mean_CMaxA_Days then 3.0 
when ags3_Mean_CMaxA_Days is null then 3.0 
else 4.0 end as PSC_ags3_Mean_CMaxA_Days 
 
, case 
when ags3_Max_CMaxA_Days < 14.5 then 4.0 
when 14.500 <= ags3_Max_CMaxA_Days then 3.0 
when ags3_Max_CMaxA_Days is null then 2.0 
else 4.0 end as PSC_ags3_Max_CMaxA_Days 
 
, case 
when 0.500 <= agr3_Min_CMaxA_Due then 4.0 
when agr3_Min_CMaxA_Due < 0.5 then 7.0 
when agr3_Min_CMaxA_Due is null then 9.0 
else 4.0 end as PSC_agr3_Min_CMaxA_Due 
 
, case 
when 0.000 <= act3_n_arrears_days then 4.0 
when act3_n_arrears_days is null then -25.0 
else 4.0 end as PSC_act3_n_arrears_days 
 
, case 
when 2.500 <= act3_n_good_days then 4.0 
when 1.5 <= act3_n_good_days  and  act3_n_good_days < 2.5 then 4.0 
when 0.5 <= act3_n_good_days  and  act3_n_good_days < 1.5 then 6.0 
when act3_n_good_days < 0.5 then 8.0 
when act3_n_good_days is null then 9.0 
else 4.0 end as PSC_act3_n_good_days 
 
, case 
when ags6_Mean_CMaxI_Days < 11.917 then 4.0 
when 13.917 <= ags6_Mean_CMaxI_Days then 4.0 
when 11.917 <= ags6_Mean_CMaxI_Days  and  ags6_Mean_CMaxI_Days < 12.367 then 4.0 
when 12.367 <= ags6_Mean_CMaxI_Days  and  ags6_Mean_CMaxI_Days < 13.917 then 4.0 
when ags6_Mean_CMaxI_Days is null then 5.0 
else 4.0 end as PSC_ags6_Mean_CMaxI_Days 
 
, case 
when agr6_Max_CMaxI_Days < 14.5 then 4.0 
when 14.500 <= agr6_Max_CMaxI_Days then -3.0 
when agr6_Max_CMaxI_Days is null then -24.0 
else 4.0 end as PSC_agr6_Max_CMaxI_Days 
 
, case 
when ags6_Max_CMaxI_Days < 13.5 then 4.0 
when 14.500 <= ags6_Max_CMaxI_Days then 0.0 
when 13.5 <= ags6_Max_CMaxI_Days  and  ags6_Max_CMaxI_Days < 14.5 then -0.0 
when ags6_Max_CMaxI_Days is null then -7.0 
else 4.0 end as PSC_ags6_Max_CMaxI_Days 
 
, case 
when 6.5 <= agr6_Min_CMaxI_Days  and  agr6_Min_CMaxI_Days < 9.5 then 4.0 
when 9.5 <= agr6_Min_CMaxI_Days  and  agr6_Min_CMaxI_Days < 10.5 then 7.0 
when agr6_Min_CMaxI_Days < 6.5 then 8.0 
when 10.500 <= agr6_Min_CMaxI_Days then 11.0 
when agr6_Min_CMaxI_Days is null then 18.0 
else 4.0 end as PSC_agr6_Min_CMaxI_Days 
 
, case 
when 0.417 <= agr6_Mean_CMaxI_Due then 4.0 
when 0.083 <= agr6_Mean_CMaxI_Due  and  agr6_Mean_CMaxI_Due < 0.417 then -16.0 
when agr6_Mean_CMaxI_Due < 0.083 then -29.0 
when agr6_Mean_CMaxI_Due is null then -53.0 
else 4.0 end as PSC_agr6_Mean_CMaxI_Due 
 
, case 
when 0.450 <= ags6_Mean_CMaxI_Due then 4.0 
when 0.083 <= ags6_Mean_CMaxI_Due  and  ags6_Mean_CMaxI_Due < 0.45 then 21.0 
when ags6_Mean_CMaxI_Due < 0.083 then 29.0 
when ags6_Mean_CMaxI_Due is null then 49.0 
else 4.0 end as PSC_ags6_Mean_CMaxI_Due 
 
, case 
when 0.000 <= agr6_Min_CMaxI_Due then 4.0 
when agr6_Min_CMaxI_Due is null then -6.0 
else 4.0 end as PSC_agr6_Min_CMaxI_Due 
 
, case 
when agr6_Mean_CMaxC_Days < 14.25 then 4.0 
when 14.25 <= agr6_Mean_CMaxC_Days  and  agr6_Mean_CMaxC_Days < 14.583 then 0.0 
when agr6_Mean_CMaxC_Days is null then -1.0 
when 14.583 <= agr6_Mean_CMaxC_Days  and  agr6_Mean_CMaxC_Days < 14.75 then -4.0 
when 14.750 <= agr6_Mean_CMaxC_Days then -7.0 
else 4.0 end as PSC_agr6_Mean_CMaxC_Days 
 
, case 
when 0.708 <= ags6_Mean_CMaxC_Due then 4.0 
when 0.367 <= ags6_Mean_CMaxC_Due  and  ags6_Mean_CMaxC_Due < 0.708 then 15.0 
when 0.183 <= ags6_Mean_CMaxC_Due  and  ags6_Mean_CMaxC_Due < 0.367 then 20.0 
when ags6_Mean_CMaxC_Due < 0.183 then 25.0 
when ags6_Mean_CMaxC_Due is null then 30.0 
else 4.0 end as PSC_ags6_Mean_CMaxC_Due 
 
, case 
when agr6_Mean_CMaxA_Days < 14.417 then 4.0 
when 14.417 <= agr6_Mean_CMaxA_Days  and  agr6_Mean_CMaxA_Days < 14.583 then 5.0 
when 14.583 <= agr6_Mean_CMaxA_Days  and  agr6_Mean_CMaxA_Days < 14.75 then 5.0 
when agr6_Mean_CMaxA_Days is null then 5.0 
when 14.750 <= agr6_Mean_CMaxA_Days then 6.0 
else 4.0 end as PSC_agr6_Mean_CMaxA_Days 
 
, case 
when 0.917 <= agr6_Mean_CMaxA_Due then 4.0 
when 0.75 <= agr6_Mean_CMaxA_Due  and  agr6_Mean_CMaxA_Due < 0.917 then 4.0 
when 0.417 <= agr6_Mean_CMaxA_Due  and  agr6_Mean_CMaxA_Due < 0.75 then 5.0 
when agr6_Mean_CMaxA_Due < 0.417 then 6.0 
when agr6_Mean_CMaxA_Due is null then 7.0 
else 4.0 end as PSC_agr6_Mean_CMaxA_Due 
 
, case 
when 0.500 <= agr6_Min_CMaxA_Due then 4.0 
when agr6_Min_CMaxA_Due < 0.5 then 35.0 
when agr6_Min_CMaxA_Due is null then 51.0 
else 4.0 end as PSC_agr6_Min_CMaxA_Due 
 
, case 
when ags9_Mean_CMaxI_Days < 11.944 then 4.0 
when 12.211 <= ags9_Mean_CMaxI_Days  and  ags9_Mean_CMaxI_Days < 12.817 then 9.0 
when 12.817 <= ags9_Mean_CMaxI_Days then 13.0 
when 11.944 <= ags9_Mean_CMaxI_Days  and  ags9_Mean_CMaxI_Days < 12.211 then 19.0 
when ags9_Mean_CMaxI_Days is null then 30.0 
else 4.0 end as PSC_ags9_Mean_CMaxI_Days 
 
, case 
when ags9_Max_CMaxI_Days < 13.5 then 4.0 
when 14.500 <= ags9_Max_CMaxI_Days then 10.0 
when 13.5 <= ags9_Max_CMaxI_Days  and  ags9_Max_CMaxI_Days < 14.5 then 11.0 
when ags9_Max_CMaxI_Days is null then 36.0 
else 4.0 end as PSC_ags9_Max_CMaxI_Days 
 
, case 
when 0.000 <= ags9_Min_CMaxI_Due then 4.0 
when ags9_Min_CMaxI_Due is null then -37.0 
else 4.0 end as PSC_ags9_Min_CMaxI_Due 
 
, case 
when 15.500 <= agr9_Max_CMaxC_Days then 4.0 
when agr9_Max_CMaxC_Days < 15.5 then -23.0 
when agr9_Max_CMaxC_Days is null then -32.0 
else 4.0 end as PSC_agr9_Max_CMaxC_Days 
 
, case 
when ags9_Min_CMaxC_Days < 11.5 then 4.0 
when 11.5 <= ags9_Min_CMaxC_Days  and  ags9_Min_CMaxC_Days < 12.5 then 5.0 
when 12.5 <= ags9_Min_CMaxC_Days  and  ags9_Min_CMaxC_Days < 13.5 then 14.0 
when ags9_Min_CMaxC_Days is null then 16.0 
when 13.500 <= ags9_Min_CMaxC_Days then 22.0 
else 4.0 end as PSC_ags9_Min_CMaxC_Days 
 
, case 
when 11.708 <= agr12_Mean_CMaxI_Days  and  agr12_Mean_CMaxI_Days < 12.208 then 4.0 
when agr12_Mean_CMaxI_Days < 11.708 then 12.0 
when 12.208 <= agr12_Mean_CMaxI_Days  and  agr12_Mean_CMaxI_Days < 13.125 then 14.0 
when 13.125 <= agr12_Mean_CMaxI_Days then 22.0 
when agr12_Mean_CMaxI_Days is null then 24.0 
else 4.0 end as PSC_agr12_Mean_CMaxI_Days 
 
, case 
when agr12_Max_CMaxI_Days < 15 then 4.0 
when 15.000 <= agr12_Max_CMaxI_Days then -3.0 
when agr12_Max_CMaxI_Days is null then -29.0 
else 4.0 end as PSC_agr12_Max_CMaxI_Days 
 
, case 
when 14.500 <= ags12_Max_CMaxI_Days then 4.0 
when 13.5 <= ags12_Max_CMaxI_Days  and  ags12_Max_CMaxI_Days < 14.5 then 3.0 
when ags12_Max_CMaxI_Days < 13.5 then -0.0 
when ags12_Max_CMaxI_Days is null then -8.0 
else 4.0 end as PSC_ags12_Max_CMaxI_Days 
 
, case 
when agr12_Min_CMaxI_Days < 5.5 then 4.0 
when 5.5 <= agr12_Min_CMaxI_Days  and  agr12_Min_CMaxI_Days < 9.5 then 4.0 
when 9.5 <= agr12_Min_CMaxI_Days  and  agr12_Min_CMaxI_Days < 10.5 then 4.0 
when 10.500 <= agr12_Min_CMaxI_Days then 4.0 
when agr12_Min_CMaxI_Days is null then 4.0 
else 4.0 end as PSC_agr12_Min_CMaxI_Days 
 
, case 
when 6.5 <= ags12_Min_CMaxI_Days  and  ags12_Min_CMaxI_Days < 9.5 then 4.0 
when 12.500 <= ags12_Min_CMaxI_Days then 4.0 
when ags12_Min_CMaxI_Days < 6.5 then 3.0 
when 9.5 <= ags12_Min_CMaxI_Days  and  ags12_Min_CMaxI_Days < 12.5 then 3.0 
when ags12_Min_CMaxI_Days is null then -0.0 
else 4.0 end as PSC_ags12_Min_CMaxI_Days 
 
, case 
when 0.437 <= ags12_Mean_CMaxI_Due then 4.0 
when 0.174 <= ags12_Mean_CMaxI_Due  and  ags12_Mean_CMaxI_Due < 0.437 then 4.0 
when 0.042 <= ags12_Mean_CMaxI_Due  and  ags12_Mean_CMaxI_Due < 0.174 then 4.0 
when ags12_Mean_CMaxI_Due < 0.042 then 4.0 
when ags12_Mean_CMaxI_Due is null then 5.0 
else 4.0 end as PSC_ags12_Mean_CMaxI_Due 
 
, case 
when 0.500 <= agr12_Max_CMaxI_Due then 4.0 
when agr12_Max_CMaxI_Due < 0.5 then -4.0 
when agr12_Max_CMaxI_Due is null then -14.0 
else 4.0 end as PSC_agr12_Max_CMaxI_Due 
 
, case 
when 0.000 <= agr12_Min_CMaxI_Due then 4.0 
when agr12_Min_CMaxI_Due is null then 52.0 
else 4.0 end as PSC_agr12_Min_CMaxI_Due 
 
, case 
when agr12_Mean_CMaxC_Days < 14.375 then 4.0 
when 14.375 <= agr12_Mean_CMaxC_Days  and  agr12_Mean_CMaxC_Days < 14.542 then 11.0 
when agr12_Mean_CMaxC_Days is null then 12.0 
when 14.542 <= agr12_Mean_CMaxC_Days  and  agr12_Mean_CMaxC_Days < 14.708 then 23.0 
when 14.708 <= agr12_Mean_CMaxC_Days then 36.0 
else 4.0 end as PSC_agr12_Mean_CMaxC_Days 
 
, case 
when agr12_Mean_CMaxA_Days < 14.375 then 4.0 
when 14.375 <= agr12_Mean_CMaxA_Days  and  agr12_Mean_CMaxA_Days < 14.542 then 4.0 
when agr12_Mean_CMaxA_Days is null then 4.0 
when 14.542 <= agr12_Mean_CMaxA_Days  and  agr12_Mean_CMaxA_Days < 14.708 then 4.0 
when 14.708 <= agr12_Mean_CMaxA_Days then 4.0 
else 4.0 end as PSC_agr12_Mean_CMaxA_Days 
 
, case 
when ags12_Min_CMaxA_Days < 8.5 then 4.0 
when 8.5 <= ags12_Min_CMaxA_Days  and  ags12_Min_CMaxA_Days < 12.5 then 4.0 
when 12.5 <= ags12_Min_CMaxA_Days  and  ags12_Min_CMaxA_Days < 13.5 then 5.0 
when ags12_Min_CMaxA_Days is null then 5.0 
when 13.500 <= ags12_Min_CMaxA_Days then 6.0 
else 4.0 end as PSC_ags12_Min_CMaxA_Days 
 
, case 
when 1.500 <= agr12_Max_CMaxA_Due then 4.0 
when 0.5 <= agr12_Max_CMaxA_Due  and  agr12_Max_CMaxA_Due < 1.5 then 5.0 
when agr12_Max_CMaxA_Due < 0.5 then 6.0 
when agr12_Max_CMaxA_Due is null then 6.0 
else 4.0 end as PSC_agr12_Max_CMaxA_Due 
 
, case 
when 1.5 <= ags12_Max_CMaxA_Due  and  ags12_Max_CMaxA_Due < 2.5 then 4.0 
when 2.500 <= ags12_Max_CMaxA_Due then 8.0 
when 0.5 <= ags12_Max_CMaxA_Due  and  ags12_Max_CMaxA_Due < 1.5 then 11.0 
when ags12_Max_CMaxA_Due < 0.5 then 14.0 
when ags12_Max_CMaxA_Due is null then 22.0 
else 4.0 end as PSC_ags12_Max_CMaxA_Due 
 
, case 
when 0.000 <= agr12_Min_CMaxA_Due then 4.0 
when agr12_Min_CMaxA_Due is null then -19.0 
else 4.0 end as PSC_agr12_Min_CMaxA_Due 
 
, case 
when 0.000 <= ags12_Min_CMaxA_Due then 4.0 
when ags12_Min_CMaxA_Due is null then -2.0 
else 4.0 end as PSC_ags12_Min_CMaxA_Due 
 
, case 
when 0.500 <= act12_n_arrears_days then 4.0 
when act12_n_arrears_days < 0.5 then 14.0 
when act12_n_arrears_days is null then 65.0 
else 4.0 end as PSC_act12_n_arrears_days 
 
, case 
when app_char_gender in ('Male') then 4.0 
when app_char_gender in ('Female') then 14.0 
else 4.0 end as PSC_app_char_gender 
 
, case 
when app_char_marital_status in ('Divorced') then 10.0 
when app_char_marital_status in ('Maried') then 13.0 
when app_char_marital_status in ('Widowed') then 15.0 
else 4.0 end as PSC_app_char_marital_status 
 
, case 
when app_char_city in ('Medium') then 4.0 
when app_char_city in ('Big') then 4.0 
when app_char_city in ('Large') then 4.0 
when app_char_city in ('Small') then 4.0 
else 4.0 end as PSC_app_char_city 
 
, case 
when app_char_home_status in ('Owner') then 4.0 
when app_char_home_status in ('Rental') then 15.0 
else 4.0 end as PSC_app_char_home_status 
 
, case 
when app_char_cars in ('Owner') then 4.0 
when app_char_cars in ('No') then 8.0 
else 4.0 end as PSC_app_char_cars 
 
/* , 1/(1+exp(-(-0.014378052555891956*(0.0+ calculated PSC_act_age+ calculated PSC_act_cc+ calculated PSC_act_loaninc+ calculated PSC_app_income+ calculated PSC_app_n_installments+ calculated PSC_app_number_of_children+ calculated PSC_app_installment+ calculated PSC_app_char_gender+ calculated PSC_app_char_marital_status+ calculated PSC_app_char_city+ calculated PSC_app_char_home_status+ calculated PSC_app_char_cars+ calculated PSC_act_call_cc+ calculated PSC_act_cins_n_loan+ calculated PSC_act_cins_min_seniority+ calculated PSC_act_cins_n_statC+ calculated PSC_act_cins_n_statB+ calculated PSC_act_cins_n_loans_act+ calculated PSC_act_cins_maxdue+ calculated PSC_act_cins_min_pninst+ calculated PSC_act_cins_utl+ calculated PSC_act_cins_cc+ calculated PSC_act_ccss_seniority+ calculated PSC_act_ccss_min_seniority+ calculated PSC_act_ccss_n_statC+ calculated PSC_act_ccss_n_statB+ calculated PSC_act_ccss_min_pninst+ calculated PSC_act_ccss_min_lninst+ calculated PSC_act_ccss_dueutl+ calculated PSC_act_ccss_cc+ calculated PSC_agr3_Min_CMaxI_Days+ calculated PSC_ags3_Max_CMaxI_Due+ calculated PSC_ags3_Mean_CMaxC_Days+ calculated PSC_ags3_Mean_CMaxC_Due+ calculated PSC_ags3_Mean_CMaxA_Days+ calculated PSC_ags3_Max_CMaxA_Days+ calculated PSC_agr3_Min_CMaxA_Due+ calculated PSC_act3_n_arrears_days+ calculated PSC_act3_n_good_days+ calculated PSC_ags6_Mean_CMaxI_Days+ calculated PSC_agr6_Max_CMaxI_Days+ calculated PSC_ags6_Max_CMaxI_Days+ calculated PSC_agr6_Min_CMaxI_Days+ calculated PSC_agr6_Mean_CMaxI_Due+ calculated PSC_ags6_Mean_CMaxI_Due+ calculated PSC_agr6_Min_CMaxI_Due+ calculated PSC_agr6_Mean_CMaxC_Days+ calculated PSC_ags6_Mean_CMaxC_Due+ calculated PSC_agr6_Mean_CMaxA_Days+ calculated PSC_agr6_Mean_CMaxA_Due+ calculated PSC_agr6_Min_CMaxA_Due+ calculated PSC_ags9_Mean_CMaxI_Days+ calculated PSC_ags9_Max_CMaxI_Days+ calculated PSC_ags9_Min_CMaxI_Due+ calculated PSC_agr9_Max_CMaxC_Days+ calculated PSC_ags9_Min_CMaxC_Days+ calculated PSC_agr12_Mean_CMaxI_Days+ calculated PSC_agr12_Max_CMaxI_Days+ calculated PSC_ags12_Max_CMaxI_Days+ calculated PSC_agr12_Min_CMaxI_Days+ calculated PSC_ags12_Min_CMaxI_Days+ calculated PSC_ags12_Mean_CMaxI_Due+ calculated PSC_agr12_Max_CMaxI_Due+ calculated PSC_agr12_Min_CMaxI_Due+ calculated PSC_agr12_Mean_CMaxC_Days+ calculated PSC_agr12_Mean_CMaxA_Days+ calculated PSC_ags12_Min_CMaxA_Days+ calculated PSC_agr12_Max_CMaxA_Due+ calculated PSC_ags12_Max_CMaxA_Due+ calculated PSC_agr12_Min_CMaxA_Due+ calculated PSC_ags12_Min_CMaxA_Due+ calculated PSC_act12_n_arrears_days+(0)))) as PD_CSS_CROSS */ 
 
, 0.0 
+ calculated PSC_act_age + calculated PSC_act_cc + calculated PSC_act_loaninc + calculated PSC_app_income + calculated PSC_app_n_installments + calculated PSC_app_number_of_children + calculated PSC_app_installment + calculated PSC_app_char_gender + calculated PSC_app_char_marital_status + calculated PSC_app_char_city + calculated PSC_app_char_home_status + calculated PSC_app_char_cars + calculated PSC_act_call_cc + calculated PSC_act_cins_n_loan + calculated PSC_act_cins_min_seniority + calculated PSC_act_cins_n_statC + calculated PSC_act_cins_n_statB + calculated PSC_act_cins_n_loans_act + calculated PSC_act_cins_maxdue + calculated PSC_act_cins_min_pninst + calculated PSC_act_cins_utl + calculated PSC_act_cins_cc + calculated PSC_act_ccss_seniority + calculated PSC_act_ccss_min_seniority + calculated PSC_act_ccss_n_statC + calculated PSC_act_ccss_n_statB + calculated PSC_act_ccss_min_pninst + calculated PSC_act_ccss_min_lninst + calculated PSC_act_ccss_dueutl + calculated PSC_act_ccss_cc + calculated PSC_agr3_Min_CMaxI_Days + calculated PSC_ags3_Max_CMaxI_Due + calculated PSC_ags3_Mean_CMaxC_Days + calculated PSC_ags3_Mean_CMaxC_Due + calculated PSC_ags3_Mean_CMaxA_Days + calculated PSC_ags3_Max_CMaxA_Days + calculated PSC_agr3_Min_CMaxA_Due + calculated PSC_act3_n_arrears_days + calculated PSC_act3_n_good_days + calculated PSC_ags6_Mean_CMaxI_Days + calculated PSC_agr6_Max_CMaxI_Days + calculated PSC_ags6_Max_CMaxI_Days + calculated PSC_agr6_Min_CMaxI_Days + calculated PSC_agr6_Mean_CMaxI_Due + calculated PSC_ags6_Mean_CMaxI_Due + calculated PSC_agr6_Min_CMaxI_Due + calculated PSC_agr6_Mean_CMaxC_Days + calculated PSC_ags6_Mean_CMaxC_Due + calculated PSC_agr6_Mean_CMaxA_Days + calculated PSC_agr6_Mean_CMaxA_Due + calculated PSC_agr6_Min_CMaxA_Due + calculated PSC_ags9_Mean_CMaxI_Days + calculated PSC_ags9_Max_CMaxI_Days + calculated PSC_ags9_Min_CMaxI_Due + calculated PSC_agr9_Max_CMaxC_Days + calculated PSC_ags9_Min_CMaxC_Days + calculated PSC_agr12_Mean_CMaxI_Days + calculated PSC_agr12_Max_CMaxI_Days + calculated PSC_ags12_Max_CMaxI_Days + calculated PSC_agr12_Min_CMaxI_Days + calculated PSC_ags12_Min_CMaxI_Days + calculated PSC_ags12_Mean_CMaxI_Due + calculated PSC_agr12_Max_CMaxI_Due + calculated PSC_agr12_Min_CMaxI_Due + calculated PSC_agr12_Mean_CMaxC_Days + calculated PSC_agr12_Mean_CMaxA_Days + calculated PSC_ags12_Min_CMaxA_Days + calculated PSC_agr12_Max_CMaxA_Due + calculated PSC_ags12_Max_CMaxA_Due + calculated PSC_agr12_Min_CMaxA_Due + calculated PSC_ags12_Min_CMaxA_Due + calculated PSC_act12_n_arrears_days  as SCORECARD_POINTS 
 
from &zbior as indataset; 
quit; 
