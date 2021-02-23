odoo.define('delivery_purolator.checkout', function (require) {
    'use strict';

    require('web.dom_ready');
    var ajax = require('web.ajax');
    var core = require('web.core');var core = require('web.core');
    var _t = core._t;
    var concurrency = require('web.concurrency');
    var dp = new concurrency.DropPrevious();
    require('root.widget');
    var $pay_button = $('#o_payment_form_pay');
    // var websiteSaleDelivery = require('website_sale_delivery.checkout');
    // var PurolatorDelivery = websiteSaleDelivery.include(
    // );

    var _onCarrierClick = function(ev) {
        $pay_button.data('disabled_reasons', $pay_button.data('disabled_reasons') || {});
        $pay_button.data('disabled_reasons').carrier_selection = true;
        $pay_button.prop('disabled', true);
        var carrier_id = $(ev.currentTarget).val();
        var values = {'carrier_id': carrier_id};
        dp.add(ajax.jsonRpc('/shop/update_carrier', 'call', values))
          .then(_handleCarrierUpdateResultBadge);
    };
    
    var $carriers = $("#delivery_carrier input[name='delivery_type']");
    $carriers.click(_onCarrierClick);

    // Wait a tick in case form is updated on page load (eg. back button on Chromium browser)
    setTimeout(function () {
        // Workaround to:
        // - update the amount/error on the label at first rendering
        // - prevent clicking on 'Pay Now' if the shipper rating fails
        if ($carriers.length > 0) {
            $carriers.filter(':checked').click();
        }
    })

    /* Handle stuff */
    $(".oe_website_sale select[name='shipping_id']").on('change', function () {
        var value = $(this).val();
        var $provider_free = $("select[name='country_id']:not(.o_provider_restricted), select[name='state_id']:not(.o_provider_restricted)");
        var $provider_restricted = $("select[name='country_id'].o_provider_restricted, select[name='state_id'].o_provider_restricted");
        if (value === 0) {
            // Ship to the same address : only show shipping countries available for billing
            $provider_free.hide().attr('disabled', true);
            $provider_restricted.show().attr('disabled', false).change();
        } else {
            // Create a new address : show all countries available for billing
            $provider_free.show().attr('disabled', false).change();
            $provider_restricted.hide().attr('disabled', true);
        }
    });

    var _handleCarrierUpdateResultBadge = function(result) {
            var $amountDelivery = $('#order_delivery span.oe_currency_value');
            var $amountUntaxed = $('#order_total_untaxed span.oe_currency_value');
            var $amountTax = $('#order_total_taxes span.oe_currency_value');
            var $amountTotal = $('#order_total span.oe_currency_value');
            var $carrier_badge = $('#delivery_carrier input[name="delivery_type"][value=' + result.carrier_id + '] ~ .badge:not(.o_delivery_compute)');
            var $compute_badge = $('#delivery_carrier input[name="delivery_type"][value=' + result.carrier_id + '] ~ .o_delivery_compute');
            var $discount = $('#order_discounted');
            var $payButton = $('#o_payment_form_pay');
            var services_id = document.getElementById('services_id');
            var services_name = document.getElementById('services_name');
            var purolator_table = document.getElementById('purolator_table');
            var puro_card = document.getElementById('puro_card');


            if ($discount && result.new_amount_order_discounted) {
                $discount.find('.oe_currency_value').text(result.new_amount_order_discounted);
                $('#delivery_carrier .badge').text(_t('Free'));
            }

            if(services_id.value == ""){
                services_name.style.display = "none";
                services_id.style.display = "none";
            }

            if (result.status === true) {
                
                $amountDelivery.text(result.new_amount_delivery);
                $amountUntaxed.text(result.new_amount_untaxed);
                $amountTax.text(result.new_amount_tax);
                $amountTotal.text(result.new_amount_total);
                $carrier_badge.children('span').text(result.new_amount_delivery);
                $carrier_badge.removeClass('d-none');
                $compute_badge.addClass('d-none');
                $pay_button.data('disabled_reasons').carrier_selection = false;
                $pay_button.prop('disabled', _.contains($pay_button.data('disabled_reasons'), true));
                // table_load.style.display = "block";
                if(result.is_free_delivery == true && result.free_delivery){
                    $carrier_badge.text(result.error_message);
                    // $amountDelivery.text(result.error_message);
                }else{

                        var length = services_id.options.length;
                        for (var i = length-1; i >= 0; i--) {
                            services_id.options[i] = null;
                        }    
                        var rates = result.purolator_service_rates;
                        var purolator_service_rates = rates;
                        // var purolator_service_rates = rates.filter(rec => rec.service_id === 'PurolatorExpress' || rec.service_id === 'PurolatorExpressU.S.' 
                        //         || rec.service_id === 'PurolatorExpressInternational' 
                        //         || rec.service_id === 'PurolatorGround');

                        var minRate = 0, services_id_value =false;
                        var rate_array = [];

                        purolator_service_rates.forEach(function(rec, index){
                            rate_array.push(rec.total_price);
                            var opt = document.createElement('option');
                            opt.appendChild(document.createTextNode(rec.name));
                            opt.value = rec.value; 
                            services_id.appendChild(opt); 
                        });  
                        if (rate_array.length > 0) {
                            minRate = Math.min.apply(null,rate_array);
                            purolator_service_rates.forEach(function(rec, index){
                                if (minRate === rec.total_price) {
                                    services_id_value = rec.value;
                                }
                            });  
                        }
                        if(purolator_service_rates.length > 0){
                            services_name.style.display = "block";
                            
                            puro_card.style.display = "block";
                            purolator_table.style.display = "block";
                            // table_load.style.display = "none";
                        }
                        if (services_id_value != false) {
                            services_id.value=services_id_value;                    
                        }
                        if(services_id.value== ""){
                            services_id.style.display = "none";
                            services_name.style.display = "none";
                            puro_card.style.display = "none";
                            purolator_table.style.display = "none";
                        }
                        else{
                            services_name.style.display = "block";
                            puro_card.style.display = "block";
                            purolator_table.style.display = "block";
                            // table_load.style.display = "none";
                        }
                        function popoulate_table(datas) {
                            var tableRef = document.getElementById('estimate_table').getElementsByTagName('tbody')[0];
                            for (let index = tableRef.childElementCount-1; index > 0; index--) {
                                tableRef.deleteRow(index);                        
                            }
                            datas.forEach(function(rec, index){
                                var tableRef = document.getElementById('estimate_table').getElementsByTagName('tbody')[0];
                                rec.service_id = rec.service_id.replace(/([a-z])([A-Z])/g, '$1 $2').replace(/([a-z])([0-9])/g, '$1 $2');
                                // rec.service_id = rec.service_id.replace(/([a-z])([0-9])/g, '$1 $2');
                                var data_arr = rec.service_id.split(" ")
                                if ((rec.service_id.slice(Math.max(rec.service_id.length - 2, 0)) == "PM") || (rec.service_id.slice(Math.max(rec.service_id.length - 2, 0)) == "AM")){
                                    var expected_time = data_arr[data_arr.length -1].replace(/([0-9])([A-Z])/g, '$1 $2');
                                }else{
                                    var expected_time = ""
                                }
                                if (expected_time.includes('9 AM')){
                                    expected_time = '9:00 AM';
                                }else if(expected_time.includes('12 PM')){
                                    expected_time = '12:00 PM';
                                }
                                rec.service_id = rec.service_id.replace(/([0-9])([A-Z])/g, '$1 $2');
                                if (rec.service_id.includes('Express')){
                                    var guaranteed = `Guaranteed<sup>✝</sup>`
                                }
                                else{var guaranteed = "       "
                                }
                                var newRow = tableRef.insertRow(tableRef.rows.length);
                                var myHtmlContent = "";
                        
                                myHtmlContent = `<tr style="border-bottom:1pt solid black;" class="border_bottom">
                                                <td align="left" valign="bottom" style="height:20px;">
                                                    <span id="lblArrivalDate" class="StaticText">${rec.expected_delivery_date} <br> ${expected_time}</br></span>
                                                </td>
                                                <td align="left" valign="bottom" style="white-space:nowrap;">
                                                    <span id="lblService" class="StaticText">${rec.service_id}<br>${guaranteed}</br></span>
                                                </td>
                                                <td align="center" style="width:350px;white-space:nowrap;">
                                                    <div class="iw_component">
                                                        <div class="rate-details" id="rate-details" style="overflow: hidden; padding-left: 2.3em;display:none;" groupname="TotalCostCollapseGroup">
                                                <table border="0" cellspacing="0" cellpadding="0">
                                                    <tbody>
                                                        <tr>
                                                            <td style="border-bottom: solid 1px white; width: 75px; white-space: nowrap;" align="left" valign="middle">
                                                                <span id="BaseCost" class="StaticText">Base Cost</span>
                                                            </td>
                                                            <td style="border-bottom: solid 1px white; width: 50px; white-space: nowrap;"
                                                                align="right" valign="top">
                                                                <span id="lblBaseCostValue" class="StaticText">$${rec.base_price}</span>
                                                            </td>
                                                        </tr>
                                                        <tr>
                                                            <td style="border-bottom: solid 1px white; width: 75px; white-space: nowrap;" align="left" valign="middle">
                                                                <span id="lblCostName" class="StaticText">Fuel Surcharge</span>
                                                            </td>
                                                            <td style="border-bottom: solid 1px white; width: 50px; white-space: nowrap;" align="right" valign="middle">
                                                                <span id="lblCostValue" class="StaticText">$${rec.surcharges}</span>
                                                            </td>
                                                        </tr>
                                                        <tr>
                                                            <td style="border-bottom: solid 1px white; width: 75px; white-space: nowrap;" align="left" valign="middle">
                                                                <span id="lblCostName" class="StaticText">GST/HST</span>
                                                            </td>
                                                            <td style="border-bottom: solid 1px white; width: 50px; white-space: nowrap;" align="right" valign="middle">
                                                                <span id="lblCostValue" class="StaticText">$${rec.taxes}</span>
                                                            </td>
                
                                                        </tr>

                                                        <tr>
                                                            <td style="border-bottom: solid 1px white; width: 75px; white-space: nowrap;" align="left" valign="middle">
                                                            </td>
                                                            <td valign="top" style="border-bottom: solid 1px white; width: 50px;">
                                                            </td>
                                                            <td style="border-bottom: solid 1px white; white-space: nowrap" valign="middle" align="right" rowspan="99">
                                                                    <input type="submit" name="btnCreateShipment" value="Ship" id="btnCreateShipment" class="button button-primary" title="Ship"/>
                                                            </td>
                                                        </tr>
                                                    </tbody>
                                                </table>
                                            </div>
                                        </div>
                                        <div class="iw_component">
                                            <div id="lTotalCost">
                                                <table style="width: 200px;" border="0" cellspacing="0" cellpadding="0">
                                                    <tbody>
                                                        <tr>
                                                            <td style="border-bottom: solid 1px white; min-width:75px;  width:75px; white-space: nowrap;" align="right" valign="bottom">
                                                            </td>
                                                            <td style="border-bottom: solid 1px white; width: 50px; white-space: nowrap; vertical-align: bottom;" align="right" valign="bottom">
                                                                <span id="txtGrandTotal1" class="StaticText">${rec.total_price}</span>
                                                            </td>
                                                            <td style="border-bottom: solid 1px white; width: 75px; white-space: nowrap;" align="right" valign="bottom">
                                                            </td>
                                                        </tr>
                                                    </tbody>
                                                </table>
                                            </div>
                                        </div>
                                    </td>
                                    <td style="display:none" class="service_id_name" id="service_id_name">
                                            ${rec.value}
                                    </td>
                                    <td align="left" style="width:20px;white-space:nowrap;">
                                        <div id="showHideLink-div" style="padding-top:0.5em">
                                            <a id="showHideLink" class="showHideLink">
                                                <img src="/delivery_purolator/static/src/images/ln-plus.png" tooltip="Expand" alt="Expand"/>
                                            </a>
                                        </div>
                                    </td>
                                            </tr>`;
                                newRow.innerHTML = myHtmlContent;
                                newRow.lastElementChild.firstElementChild.firstElementChild.addEventListener("click", function _onshowHideLink(ev) {
                                    var row_no = ev.currentTarget.parentElement.parentElement.parentElement.rowIndex;
                                    var src = ev.currentTarget.firstElementChild.src.split("/");
                                    if (src[src.length - 1] == 'ln-plus.png'){
                                        ev.currentTarget.firstElementChild.src = '/delivery_purolator/static/src/images/ln-minus.png';
                                        ev.currentTarget.parentElement.parentElement.parentElement.children[2].children[0].firstElementChild.style.display = 'block';
                                    }
                                    else if  (src[src.length - 1] == 'ln-minus.png'){
                                        ev.currentTarget.firstElementChild.src = '/delivery_purolator/static/src/images/ln-plus.png';
                                        ev.currentTarget.parentElement.parentElement.parentElement.children[2].children[0].firstElementChild.style.display = 'none';
                                    }
                                    
                                });

                                
                                newRow.children[2].firstElementChild.firstElementChild.firstChild.firstElementChild.children[3].children[2].children[0].addEventListener("click", function _onButtonClick(ev) {
                                    var self = this;    
                                    var row_no = ev.target.parentElement.parentElement.parentElement.parentElement.parentElement.parentElement.parentElement.parentElement.rowIndex;
                                    var row =  ev.target.parentElement.parentElement.parentElement.parentElement.parentElement.parentElement.parentElement.parentElement;
                                    var service_id = row.cells[3].innerText.replace(/[^0-9]/g,'');
                                    var $carriers = $('#delivery_carrier input[name="delivery_type"]');
                                    var carrier_id = $carriers.filter(':checked')[0].value
                                    
                                    var values = {'service_id':service_id, 'carrier_id': carrier_id};
                                    dp.add(ajax.jsonRpc('/shop/update_carrier_service', 'call', values))
                                    .then(function _handleCarrierUpdateResultBadgeExtend(result) {  
                                            var $carriers = $('#delivery_carrier input[name="delivery_type"]');         
                                            if ($carriers.length > 0) {
                                                var carrier = $carriers.filter(':checked')
                                                if(carrier.length == 1){
                                                    var $amountDelivery = $('#order_delivery span.oe_currency_value');
                                                    var $amountUntaxed = $('#order_total_untaxed span.oe_currency_value');
                                                    var $amountTax = $('#order_total_taxes span.oe_currency_value');
                                                    var $amountTotal = $('#order_total span.oe_currency_value');
                                                    var $carrierBadge = $('#delivery_carrier input[name="delivery_type"][value=' + $carriers.filter(':checked')[0].value + '] ~ .badge:not(.o_delivery_compute)');
                                                    $carrierBadge.children('span').text(result.new_amount_delivery);
                                                    // $carrierBadge.removeClass('d-none');
                                                    // $compute_badge.addClass('d-none');

                                                    if (result.status === true) {
                                                        $amountDelivery.html(result.new_amount_delivery);
                                                        $amountUntaxed.html(result.new_amount_untaxed);
                                                        $amountTax.html(result.new_amount_tax);
                                                        $amountTotal.html(result.new_amount_total); 
                                                    }
                                                }                       
                                            } 
                                        });
                                });
                                    
                            });   
                        }
                        popoulate_table(purolator_service_rates);
                        var tableRef = document.getElementById('estimate_table').getElementsByTagName('tbody')[0];
                        for(var index=1;index<tableRef.childElementCount;index++){
                            if(tableRef.children[index].children[2].innerText.replace(/\s/g, '') == minRate){
                                tableRef.children[index].children[4].children[0].children[0].click()
                            }
                        }
                        if (purolator_service_rates.length > 0) {
                            purolator_table.style.display = "block";
                        }
                    } 
                }

            else {
                console.error(result.error_message);
                $compute_badge.text(result.error_message);
                $amountDelivery.text(result.new_amount_delivery);
                $amountUntaxed.text(result.new_amount_untaxed);
                $amountTax.text(result.new_amount_tax);
                $amountTotal.text(result.new_amount_total);
            }
            

        };
        

});


function sortTable(n) {
    var table, rows, switching, i, x, y, shouldSwitch, dir, switchcount = 0;
    table = document.getElementById("estimate_table");
    switching = true;
    var sort_type = document.getElementById("sort_type");
    dir = sort_type.value;

    while (switching) {
      // Start by saying: no switching is done:
      switching = false;
      rows = table.rows;
      /* Loop through all table rows (except the
      first, which contains table headers): */
      for (i = 1; i < (rows.length - 1); i++) {
        // Start by saying there should be no switching:
        shouldSwitch = false;
        /* Get the two elements you want to compare,
        one from current row and one from the next: */
        x = rows[i].getElementsByTagName("TD")[n];
        y = rows[i + 1].getElementsByTagName("TD")[n];
        x = x.innerText.toLowerCase();
        y = y.innerText.toLowerCase();
        // // -------------------------------------------
        // if(n==2){
        //     if(x.includes('base')){
        //         x = x.split("\n\t\t\n\t")[1].split("\t")[0];
               
        //     }
        //     if(y.includes('base')){
        //         y = y.split("\n\t\t\n\t")[1].split("\t")[0];
        //     }
        // }
        // // --------------------------------------

        if (dir == "asc") {
          if (x > y) {
            shouldSwitch = true;
            break;
          }
        } else if (dir == "desc") {
          if (x < y) {
            // If so, mark as a switch and break the loop:
            shouldSwitch = true;
            break;
          }
        }
      }
      if (shouldSwitch) {
        /* If a switch has been marked, make the switch
        and mark that a switch has been done: */
        rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
        switching = true;
        // Each time a switch is done, increase this count by 1:
        switchcount ++;
      } 
    //   else {
    //     /* If no switching has been done AND the direction is "asc",
    //     set the direction to "desc" and run the while loop again. */
    //     if (switchcount == 0 && dir == "asc") {
    //       dir = "desc";
    //       switching = true;
    //     }
    //   }
    }


  };


function rating_sort(n) {
    var rating_sort = document.getElementById("rating_sort");
    sortTable(rating_sort.value)



  }