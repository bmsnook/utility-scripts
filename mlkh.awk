#!/usr/local/bin/gawk -f

function just_do_it() {
	printf "Just Do It!\n"
}

function get_first_char(word) {
	return substr(tolower(word),1,1)
}

{
	hd_1 = sprintf("%s/%s",get_first_char($1),$1)
	hd_2 = sprintf("%s/%s",get_first_char($2),$2)

	cmd_make_link_1=sprintf("[[ -e %s ]] || mkdir -p -- %s && cd -- %s && ln -s ../../%s && cd ../..",hd_1,hd_1,hd_1,hd_2)
	cmd_make_link_2=sprintf("[[ -e %s ]] || mkdir -p -- %s && cd -- %s && ln -s ../../%s && cd ../..",hd_2,hd_2,hd_2,hd_1)
	cmd_open_1=sprintf("open %s",hd_1)
	cmd_open_2=sprintf("open %s",hd_2)

	print(cmd_make_link_1)
	system(cmd_make_link_1)
	close(cmd_make_link_1)

	print(cmd_make_link_2)
	system(cmd_make_link_2)
	close(cmd_make_link_2)

	print(cmd_open_1)
	system(cmd_open_1)
	close(cmd_open_1)

	print(cmd_open_2)
	system(cmd_open_2)
	close(cmd_open_2)
}
