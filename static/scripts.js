// list of ingredients
var ingredients = [];

/** LOGIN **/

function validateUserDetails(user_name){

  console.log(user_name);

  var info_return;

  $.ajax({
  url: '/username_check',//'response.php?type=validateUserDetails',
  type: 'GET',
  async: false,
  dataType: 'json',
  data: {"name": user_name},
  success: function(data){
        console.log(data);
        info_return = data.taken;

        }
  });

  return info_return;
}


//ensures valid entrys to register
function registerCheck(){
  var a = document.forms["register"]["username"].value;
  var b = document.forms["register"]["name"].value;
  var c = document.forms["register"]["surname"].value;
  var d = document.forms["register"]["password"].value;
  var e = document.forms["register"]["confirmation"].value;

  //return false if any fields not completed return alert
  if (a == "" || b == "" || c == "" || d == "" || e == ""){
    alert("All fields are required");
    return false;
  }

  //return false if password and confirmation do not match
  if (d != e) {
    alert("Passwords entered do not match");
    return false;
  }

  // ajax request username
  var info = validateUserDetails(a);
  console.log("DATA = " + info);

  if(info != "not taken"){
    alert("That username is already in use, please enter another");
    return false;
  }
}



/** FOOD SEARCH **/

//ensures valid inputs to food search
function validSearch(){
  var x = document.forms["search"]["name"].value;

  if (x == "") {
    alert("name of food type must be entered");
    return false;
  }
}

function searchCheck(id){
  var a = "hour_" + id;
  var b = "minute_" + id;
  var c = "am_pm_" + id;

  var x = document.getElementById(a).value;
  var y = document.getElementById(b).value;
  var z = document.getElementById(c).value;

  if (x == "" || y == "" || z == "") {
    alert("Please enter the time when this food was eaten");
    return false;
  }

}

// show/hide form entrys in food search page
function searchToDiary(div){
    var x = document.getElementById(div);

    if (x.style.display === "none") {
        x.style.display = "inline";
    }
    else {
        x.style.display = "none";
    }
}


/** UNIVERSAL **/

// checks valid entry into diary - both food input from favorites and allergic reations
function validDiaryEntry() {

  var v = document.getElementById("input_").value;
  var w = document.getElementById("day_").value;
  var x = document.getElementById("hour_").value;
  var y = document.getElementById("minute_").value;
  var z = document.getElementById("am_pm_").value;

  if (v  == "" || w == "" || x == "" || y == "" || z == "") {
    alert("all fields must be completed");
    return false;
  }
}


/** INPUT FOOD REGISTER **/

//ensures valid entries into input_food food register
function validFoodEntry() {
  var x = document.forms["foodInput"]["brand"].value;
  var y = document.forms["foodInput"]["name"].value;
  var z = document.forms["foodInput"]["ingred1"].value;

    if (x == "") {
        alert("Brand must be filled out");
        return false;
    }
    else if (y == "") {
        alert("Name must be filled out");
        return false;
    }
    else if (z == "") {
        alert("At least one ingredient must be entered");
        return false;
    }

    else {
      var r = confirm("Are you sure the information entered is correct?")
        if (r == false) {
            return false;
          }
    }
}

// expand ingredients form to allow addition of up to 20 ingredients
function newIngredient() {

  // code from http://charlie.griefer.com/blog/2009/09/17/jquery-dynamically-adding-form-elements/index.html

  var num = $('.ingredients').length;   // how many "duplicatable" input fields we currently have
  var newNum  = (num + 1);    // the numeric ID of the new input field being added

  // create the new element via clone(), and manipulate it's ID using newNum value
  var newElem = $('#ingred' + num).clone().attr('id', 'ingred' + newNum);

  // manipulate the name/id values of the input inside the new element
  newElem.children(':first').val('');
  newElem.children(':first').attr('name', 'ingred' + newNum).attr('placeholder', 'ingredient ' + newNum); // .attr('value', "").attr('id', 'ingred' + newNum)

  // insert the new element after the last "duplicatable" input field
  $('#ingred' + num).after(newElem);

  // enable the "remove" button
  $('#delIngred').attr('disabled','');

  // you can only add 20 ingredients
  if (newNum == 20) {
    $('#addIngred').attr('disabled','disabled');
  };

  //focus on the new ingredient box when reloading the page
  $(document).ready(function () {

    $('#ingred' + newNum).focus();

  });
}


// allow removal of an ingredient and deletion of the form box
function lessIngredient() {
  var num = $('.ingredients').length; // how many "duplicatable" input fields we currently have

  // if only one element remains, disable the "remove" button
  if (num-1 == 1) {
    $('#delIngred').attr('disabled','disabled');
  }

  $('#ingred' + num).remove();

  // enable the "add" button
  $('#addIngred').attr('disabled','');
}


// clear all currently entered ingredients from list
function clearIngreds() {
  var num = $('.ingredients').length; // how many "duplicatable" input fields we currently have

  while (num > 1) {
    lessIngredient()
    num--;
  }
}


// offer user opportunity not to delete item from diary
function checkSubmit(brand, name) {
  var r = confirm("Are you sure you want to delete " + brand + " " + name + " from your diary?");

  if (r == false) {
    return false;
  }
}


// click function on diary calendar
function myDateFunction(id, fromModal) {

        //hide any open windows
        if (fromModal) {
          $("#" + id + "_modal").modal("hide");
        }

        // info for date clicked
        var date = $("#" + id).data("date");
        var hasEvent = $("#" + id).data("hasEvent");

        if (hasEvent && fromModal) {
          return date;
        }
}


// shows the ingredients of a food selected on faves page
function showIngredients(food_id) {

  let parameters = {
    q: food_id
  };

  // get json info of ingredients from python
  $.getJSON("/ingredients_text", parameters, function(data) {
    // put info into text for div
    text = "Ingredients: " + data.ingredient

    //insert info into div
    document.getElementById("ingredients").innerHTML = text;
    document.getElementById("ingredients").style.display = 'block';

    });

}

function validTimes(){
  var start = document.getElementById("start_slider").value;
  var end = document.getElementById("end_slider").value;
  var name = document.getElementById("title").value;


  if (name == ""){
    alert("Enter a name for your reaction");
    return false;
  }

  if (end >= start){
    alert("The end of your rection window is currently before the start, please update it");
    return false;
  }

  else {
    var r = confirm("Are you sure the information entered is correct? PLease check before submission");
      if (r == false) {
          return false;
        }
    }

}
