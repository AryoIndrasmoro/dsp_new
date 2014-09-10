
%for picking in objects:
	
	<table style="">
		<tr>
			<td><b>Customer Address:</b></td>
		</tr>
		<tr>
			<td>${picking.partner_id.title} ${picking.partner_id.name}</td>									
		</tr>
		<tr>
			<td>${display_address(picking.partner_id)}</td>				
		</tr>		
		<tr>
			<td>${picking.partner_id.email}</td>
		</tr>		
	</table>
	
	<table>
		<tr>
			<td><h1>Delivery Order : ${picking.name}</h1></td>
		</tr>
	</table>
	
	<br/>
	
	<table class="list_table">   
		<thead> 
	      <tr>
	        <th>Journal</td>
	        <th>Order(Origin)</th>
	        <th>Schedule Date</th>
	        <th>Weight</th>
	      </tr>	      
	    </thead>
	    <tbody>
	      <tr>
	        <td>
	          ${picking.stock_journal_id.name}
	        </td>
	        <td>
	          ${picking.origin or ''}
	        </td>
	        <td>
	          ${formatLang(picking.min_date,date_time = True) }
	        </td>
	        <td>
	          ${'weight' in picking._columns.keys() and picking.weight or ''}
	        </td>
	      </tr>
	      </tbody>	      
	</table>
	<br/>
	
	<table>
      <tr>
      	<td></td>
        <td>
          Description
        </td>
        <td>
          Serial Number
        </td>
        <td>
          Status
        </td>
        <td>
			Location
        </td>
        <td>
			Quantity 
        </td>
      </tr>	
	  <tbody>
      %for move_lines in picking.move_lines:       
        <tr>
          <td>
          	${helper.embed_image("png",move_lines.product_id.image_medium)}
          </td>
          <td>          	 
             ${move_lines.product_id.name_template}
          </td>
          <td>
            ${(move_lines.prodlot_id.name) or '' }
          </td>
          <td>
            ${move_lines.state}
          </td>
          <td>
            ${(move_lines.location_id.name) or '' } 
          </td>
          <td>
            ${formatLang(move_lines.product_qty) } ${move_lines.product_uom.name }
          </td>
        </tr>
  	  %endfor
  	  </tbody>
	</table>
	
	<br/><br/>
	
	<div>Remark :</div>      
    <table>
      <tr>
        <td>
          Finance
        </td>
        <td>
          Warehouse
        </td>
        <td>
          Logistic
        </td>
        <td>
          Driver
        </td>
        <td>
          Outlet/Customer
        </td>        
      </tr>
      <tr>
        <td>
			<br/>		    		         
        </td>
        <td>
			<br/><br/>	    
        </td>
        <td>
			<br/><br/>
		    		    
        </td>
        <td>
			<br/><br/>		    		   
        </td>
        <td>
			<br/><br/>			              
        </td>      
      </tr>
    </table>
    <table>
      <tr>
        <td>
          (...........................)
        </td>
        <td>
          (...........................)
        </td>
        <td>
          (...........................)
        </td>
        <td>
          (...........................)
        </td>
        <td>
          (...........................)
        </td>                                 
      </tr>
    </table>    
    <table>
      <tr>
        <td>
          Date : 
        </td>
        <td>
          Date : 
        </td>
        <td>
          Date : 
        </td>
        <td>
          Date : 
        </td>
        <td>
          Date : 
        </td>                                 
      </tr>        
    </table>	
%endfor		
