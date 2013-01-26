$(document).ready(function(){
	$('img.downsampled').click(function(){
		other_file = $(this).attr('fullsize');
		$(this).attr('fullsize', $(this).attr('src'));
		$(this).attr('src', other_file);
	});
});